"""
Módulo de Extracción para InvoiceToSheet.
Implementa un pipeline de extracción híbrido:
1. Lectura en memoria con pdfplumber.
2. Fallback a OCR (pytesseract/pdf2image) para PDFs escaneados o imágenes.
3. Fallback opcional a LLM (OpenAI Structured Outputs) si se configura API Key.
4. Motor de reglas con Expresiones Regulares (Regex) de alta tolerancia y normalización matemática.
"""

import io
import os
import re
import logging
from typing import Optional, Tuple
from datetime import datetime

import pdfplumber
from schemas import InvoiceData

logger = logging.getLogger("InvoiceExtractor")
logging.basicConfig(level=logging.INFO)

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Intentar importar dependencias de OCR opcionales
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
    # Soporte para ruta personalizada de Tesseract en Windows
    tess_path = os.getenv("TESSERACT_PATH")
    if tess_path and os.path.exists(tess_path):
        pytesseract.pytesseract.tesseract_cmd = tess_path
except ImportError:
    OCR_AVAILABLE = False

# Intentar importar OpenAI para fallback con LLM
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# =====================================================================
# UTILIDADES DE NORMALIZACIÓN
# =====================================================================

def normalize_amount(raw_val: Optional[str]) -> float:
    """
    Normaliza representaciones numéricas monetarias complejas a float.
    Maneja:
      - '1,234.50' (formato US/UK)
      - '1.234,50' (formato hispano/europeo)
      - '1234,50' y '1234.50'
      - Espacios y símbolos de divisas ($ 1 234,50)
    """
    if not raw_val:
        return 0.0

    # Limpiar caracteres no numéricos excepto coma, punto y signo menos
    cleaned = re.sub(r"[^\d,\.\-]", "", str(raw_val)).strip()
    if not cleaned:
        return 0.0

    # Si contiene tanto punto como coma:
    if "." in cleaned and "," in cleaned:
        last_dot = cleaned.rfind(".")
        last_comma = cleaned.rfind(",")
        if last_dot > last_comma:
            # Formato 1,234.50 -> eliminar comas
            cleaned = cleaned.replace(",", "")
        else:
            # Formato 1.234,50 -> eliminar puntos y cambiar coma por punto
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        # Solo tiene comas: determinar si es decimal o miles
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            # Es decimal: 1234,50 -> 1234.50
            cleaned = cleaned.replace(",", ".")
        else:
            # Es separador de miles: 1,234 -> 1234
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        # Solo tiene puntos
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            # Podría ser miles sin decimales: 125.000 -> 125000 (común en CLP, COP, etc.)
            # Para mayor seguridad, si hay 3 dígitos exactos al final y no hay otro separador,
            # verificamos si el valor es mayor a 1000
            pass  # Se mantiene flotante por defecto a menos que se use entero
    
    try:
        return round(float(cleaned), 2)
    except (ValueError, TypeError):
        return 0.0


def normalize_date(raw_date: Optional[str]) -> str:
    """
    Normaliza fechas variadas al estándar ISO (YYYY-MM-DD).
    Soporta formatos numéricos y textuales (en español e inglés).
    """
    if not raw_date:
        return "No identificada"

    raw_date = raw_date.strip()

    # Mapeo de meses en español e inglés
    meses = {
        "enero": "01", "ene": "01", "january": "01", "jan": "01",
        "febrero": "02", "feb": "02", "february": "02",
        "marzo": "03", "mar": "03", "march": "03",
        "abril": "04", "abr": "04", "april": "04", "apr": "04",
        "mayo": "05", "may": "05",
        "junio": "06", "jun": "06", "june": "06",
        "julio": "07", "jul": "07", "july": "07",
        "agosto": "08", "ago": "08", "august": "08", "aug": "08",
        "septiembre": "09", "sep": "09", "setiembre": "09", "september": "09",
        "octubre": "10", "oct": "10", "october": "10",
        "noviembre": "11", "nov": "11", "november": "11",
        "diciembre": "12", "dic": "12", "december": "12", "dec": "12"
    }

    # Caso 1: Fechas con texto ("15 de enero de 2024", "22 de Octubre del 2023" o "15 Jan 2024")
    text_match = re.search(
        r"(\d{1,2})\s*(?:de|\/|-)?\s*([A-Za-z]{3,10})\s*(?:de|del|\/|-|,)?\s*(\d{4})",
        raw_date,
        re.IGNORECASE
    )
    if text_match:
        dia, mes_str, anio = text_match.groups()
        mes_key = mes_str.lower()
        if mes_key in meses:
            return f"{anio}-{meses[mes_key]}-{int(dia):02d}"

    # Caso 2: Formatos numéricos DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY/MM/DD
    formatos = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
        "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y"
    ]
    
    # Extraer segmento que parezca fecha
    candidate = re.search(r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4})\b", raw_date)
    date_to_test = candidate.group(1) if candidate else raw_date

    for fmt in formatos:
        try:
            dt = datetime.strptime(date_to_test, fmt)
            # Asegurar año coherente
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return raw_date[:25]


# =====================================================================
# MOTOR DE EXTRACCIÓN POR REGLAS (REGEX HEURÍSTICO)
# =====================================================================

class RegexExtractor:
    """
    Extractor de alta velocidad y tolerancia para facturas usando expresiones regulares.
    Optimizado para formatos hispanohablantes (México, España, Chile, Colombia, Perú, Argentina)
    e internacionales.
    """

    PATTERNS_INVOICE_NUMBER = [
        r"(?:factura|invoice|folio|comprobante|recibo|bill\s*no\.?)\s*(?:n[º°o#\.]?|n[uú]mero)?\s*[:#\-\s]*([A-Z0-9][A-Z0-9\-_/]{1,25})\b",
        r"\b(?:n[º°o#\.]|n[uú]mero|folio)\s*[:#\-\s]*([A-Z0-9][A-Z0-9\-_/]{1,25})\b",
        r"\b([A-Z]{1,3}-\d{4,10})\b"
    ]

    PATTERNS_DATES = [
        r"(?:fecha\s*(?:de)?\s*(?:emisi[oó]n|expedici[oó]n|factura)?|date|emisi[oó]n)\s*[:#\-\s]*([0-9]{1,2}[-/\.][0-9]{1,2}[-/\.][0-9]{2,4})",
        r"(?:fecha\s*(?:de)?\s*(?:emisi[oó]n|expedici[oó]n|factura)?|date|emisi[oó]n)\s*[:#\-\s]*([0-9]{4}[-/\.][0-9]{1,2}[-/\.][0-9]{1,2})",
        r"(?:fecha|emisi[oó]n)\s*[:#\-\s]*([0-9]{1,2}\s*(?:de)?\s*[A-Za-z]{3,10}\s*(?:de)?\s*[0-9]{4})"
    ]

    PATTERNS_TAX_ID = {
        "RFC": r"\b([A-Z&Ñ]{3,4}\s*-?\s*\d{6}\s*-?\s*[A-Z0-9]{3})\b",
        "RUT": r"\b(\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK])\b",
        "NIF_CIF": r"\b([A-HJ-NP-SUVW]\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])\b",
        "RUC": r"\b((?:10|15|17|20)\d{9}|\d{13})\b",
        "GENERIC": r"(?:R\.?F\.?C\.?|R\.?U\.?T\.?|N\.?I\.?F\.?|C\.?I\.?F\.?|R\.?U\.?C\.?|NIT|Tax\s*ID|VAT\s*(?:No|ID)?)\s*[:#\-\s]*([A-Z0-9\.\-]{6,20})\b"
    }

    PATTERNS_TOTAL = [
        r"(?:total\s*(?:a\s*pagar|general|factura|comprobante)?|importe\s*total|grand\s*total|monto\s*total)\s*[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)",
        r"(?:\bTOTAL\b)\s*[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)"
    ]

    PATTERNS_SUBTOTAL = [
        r"(?:subtotal|sub-total|sub\s*total|base\s*imponible|base\s*gravada|importe\s*neto|neto)\s*[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)",
        r"(?:\bSUBTOTAL\b)\s*[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?)"
    ]

    PATTERNS_TAXES = [
        r"(?:i\.?v\.?a\.?|impuesto(?:s)?|vat|igv|tax)\s*(?:\(?\d{1,2}%?\)?\s*)?[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)",
        r"(?:16%|21%|19%|18%)\s*[:=]?\s*([$€£S/\.\s]*[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?)"
    ]

    CURRENCY_INDICATORS = {
        "MXN": ["MXN", "PESOS MEXICANOS", "M.N."],
        "EUR": ["EUR", "€", "EUROS"],
        "USD": ["USD", "US$", "DOLARES", "DOLLARS"],
        "CLP": ["CLP", "PESOS CHILENOS"],
        "COP": ["COP", "PESOS COLOMBIANOS"],
        "PEN": ["PEN", "S/.", "SOLES"],
        "ARS": ["ARS", "PESOS ARGENTINOS"],
        "GBP": ["GBP", "£", "POUNDS"]
    }

    @classmethod
    def extract(cls, text: str, filename: str) -> InvoiceData:
        """
        Ejecuta la extracción de datos sobre el texto plano extraído del PDF.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        full_text = " ".join(lines)

        # 1. Número de Factura
        num_factura = "No identificado"
        for pattern in cls.PATTERNS_INVOICE_NUMBER:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # Filtrar palabras clave erróneas
                if candidate.lower() not in ["de", "del", "fecha", "cliente", "total"]:
                    num_factura = candidate
                    break

        # 2. Fecha de Emisión
        raw_date = "No identificada"
        for pattern in cls.PATTERNS_DATES:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_date = match.group(1).strip()
                break
        fecha_emision = normalize_date(raw_date)

        # 3. ID Fiscal del Proveedor (Emisor)
        id_fiscal = "No identificado"
        # Búsqueda prioritaria por tipo común
        for tax_type, pattern in cls.PATTERNS_TAX_ID.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                id_fiscal = match.group(1).strip()
                break

        # 4. Nombre del Proveedor (Emisor)
        nombre_proveedor = "No identificado"
        # Heurística a: Etiqueta explícita
        prov_match = re.search(
            r"(?:emisor|de|proveedor|vendedor|raz[oó]n\s*social|empresa|company)\s*[:\-]\s*([^\n\r,]{3,60})",
            text,
            re.IGNORECASE
        )
        if prov_match:
            candidate = prov_match.group(1).strip()
            if not any(k in candidate.lower() for k in ["factura", "cliente", "fecha", "rfc", "nif"]):
                nombre_proveedor = candidate
        
        # Heurística b: Las primeras líneas del encabezado (antes del cliente y tax ID)
        if nombre_proveedor == "No identificado" and lines:
            for l in lines[:5]:
                # Si parece un nombre de empresa comercial o tiene sufijo empresarial
                if re.search(r"\b(S\.?A\.?|S\.?L\.?|S\.?A\.?S\.?|S\.?R\.?L\.?|C\.?V\.?|LLC|INC|CORP|GMBH|S\.?C\.?)\b", l, re.IGNORECASE):
                    nombre_proveedor = l
                    break
            # Si aún no se encuentra, tomar la primera línea legible no numérica
            if nombre_proveedor == "No identificado" and len(lines[0]) > 3:
                if not re.search(r"(factura|invoice|folio|\d{4})", lines[0], re.IGNORECASE):
                    nombre_proveedor = lines[0][:60]

        # 5. Nombre del Cliente (Receptor)
        nombre_cliente = None
        cliente_match = re.search(
            r"(?:cliente|receptor|facturado\s*a|billed\s*to|para|customer|se[ñn]or(?:es)?)\s*[:\-]\s*([^\n\r,]{3,60})",
            text,
            re.IGNORECASE
        )
        if cliente_match:
            candidate = cliente_match.group(1).strip()
            if not any(k in candidate.lower() for k in ["rfc", "nif", "cif", "fecha", "direcci"]):
                nombre_cliente = candidate

        # 6. Moneda
        moneda = "USD"
        found_currency = False
        for curr_code, indicators in cls.CURRENCY_INDICATORS.items():
            for ind in indicators:
                if re.search(r"\b" + re.escape(ind) + r"\b", text, re.IGNORECASE):
                    moneda = curr_code
                    found_currency = True
                    break
            if found_currency:
                break
        
        # Si se detectó un RFC mexicano y la moneda quedó en USD, probablemente sea MXN
        if not found_currency and "RFC" in text.upper():
            moneda = "MXN"
        elif not found_currency and ("€" in text or "EUR" in text.upper()):
            moneda = "EUR"

        # 7. Subtotal, Impuestos y Total
        total_val = 0.0
        for pattern in cls.PATTERNS_TOTAL:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                # Tomar la última coincidencia (habitualmente en el pie de página)
                last_match = matches[-1].group(1)
                total_val = normalize_amount(last_match)
                if total_val > 0:
                    break

        subtotal_val = 0.0
        for pattern in cls.PATTERNS_SUBTOTAL:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                last_match = matches[-1].group(1)
                subtotal_val = normalize_amount(last_match)
                if subtotal_val > 0:
                    break

        impuestos_val = 0.0
        for pattern in cls.PATTERNS_TAXES:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                last_match = matches[-1].group(1)
                impuestos_val = normalize_amount(last_match)
                if impuestos_val > 0:
                    break

        # Reconciliación matemática básica
        if subtotal_val > 0 and total_val > 0 and impuestos_val == 0.0:
            if total_val > subtotal_val:
                impuestos_val = round(total_val - subtotal_val, 2)
        elif total_val == 0.0 and (subtotal_val > 0 or impuestos_val > 0):
            total_val = round(subtotal_val + impuestos_val, 2)
        elif total_val > 0 and subtotal_val == 0.0 and impuestos_val > 0:
            subtotal_val = round(total_val - impuestos_val, 2)

        # Determinar estado
        estado = "success"
        mensaje_error = None
        if total_val == 0.0 or num_factura == "No identificado":
            estado = "warning"
            mensaje_error = "Se requiere revisión: Total o Número de Factura no confirmados."

        return InvoiceData(
            numero_factura=num_factura,
            fecha_emision=fecha_emision,
            nombre_proveedor=nombre_proveedor,
            id_fiscal_proveedor=id_fiscal,
            nombre_cliente=nombre_cliente,
            subtotal=subtotal_val,
            impuestos=impuestos_val,
            total=total_val,
            moneda=moneda,
            nombre_archivo_origen=filename,
            estado=estado,
            mensaje_error=mensaje_error,
            metodo_extraccion="regex"
        )


# =====================================================================
# FALLBACK 1: OCR CON PYTESSERACT (PARA PDFs ESCANEADOS)
# =====================================================================

def extract_text_with_ocr(pdf_bytes: bytes) -> Optional[str]:
    """
    Convierte las primeras páginas del PDF en imágenes y extrae texto vía pytesseract.
    """
    if not OCR_AVAILABLE:
        logger.warning("pytesseract o pdf2image no están disponibles en el entorno.")
        return None

    try:
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=2)
        full_ocr_text = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang="spa+eng")
            full_ocr_text.append(text)
        return "\n".join(full_ocr_text)
    except Exception as e:
        logger.error(f"Error durante la ejecución del OCR: {e}")
        return None


# =====================================================================
# FALLBACK 2: LLM ESTRUCTURADO (OPENAI)
# =====================================================================

def extract_with_llm(raw_text: str, filename: str) -> Optional[InvoiceData]:
    """
    Fallback usando OpenAI con structured outputs para documentos complejos o desordenados.
    Se activa únicamente si OPENAI_API_KEY está configurada en el entorno.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OPENAI_AVAILABLE:
        return None

    try:
        client = OpenAI(api_key=api_key)
        prompt = (
            "Eres un asistente contable de precisión. Extrae los datos clave de la siguiente factura "
            "y responde estrictamente conforme al esquema especificado."
        )

        response = client.beta.chat.completions.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Archivo: {filename}\n\nTexto de la factura:\n{raw_text[:4000]}"}
            ],
            response_format=InvoiceData,
            temperature=0.0
        )
        parsed: InvoiceData = response.choices[0].message.parsed
        parsed.nombre_archivo_origen = filename
        parsed.metodo_extraccion = "llm"
        return parsed
    except Exception as e:
        logger.error(f"Error en fallback LLM: {e}")
        return None


# =====================================================================
# FUNCIÓN PRINCIPAL DE EXTRACCIÓN (PIPELINE)
# =====================================================================

def extract_invoice_from_pdf(pdf_bytes: bytes, filename: str) -> InvoiceData:
    """
    Pipeline principal para procesar un único archivo PDF en memoria:
    1. Abre con pdfplumber y extrae texto.
    2. Si el texto es nulo o escaso, recurre a OCR.
    3. Ejecuta el extractor Regex.
    4. Si los resultados de regex son insuficientes y hay LLM configurado, usa fallback LLM.
    5. Maneja excepciones de encriptación o corrupción.
    """
    if not pdf_bytes or len(pdf_bytes) == 0:
        return InvoiceData(
            nombre_archivo_origen=filename,
            estado="error",
            mensaje_error="El archivo está vacío (0 bytes)."
        )

    extracted_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Procesar las primeras 3 páginas (habitual para facturas)
            pages_text = []
            for page in pdf.pages[:3]:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)
            extracted_text = "\n".join(pages_text).strip()
    except Exception as e:
        err_msg = str(e)
        logger.warning(f"Error abriendo PDF con pdfplumber '{filename}': {err_msg}")
        if "password" in err_msg.lower():
            return InvoiceData(
                nombre_archivo_origen=filename,
                estado="error",
                mensaje_error="El archivo PDF está protegido con contraseña."
            )
        # Si falla la apertura estándar, intentamos verificar si es legible con OCR
        pass

    # Si no se extrajo suficiente texto (posible PDF escaneado / imagen)
    used_ocr = False
    if len(extracted_text) < 40:
        ocr_text = extract_text_with_ocr(pdf_bytes)
        if ocr_text and len(ocr_text.strip()) > 30:
            extracted_text = ocr_text.strip()
            used_ocr = True

    # Si aún no hay texto tras intentar OCR
    if not extracted_text or len(extracted_text.strip()) < 15:
        return InvoiceData(
            nombre_archivo_origen=filename,
            estado="error",
            mensaje_error="No se pudo extraer texto. Es posible que sea un escaneo sin OCR o un archivo dañado."
        )

    # Paso 3: Extracción vía Reglas y Heurísticas
    result = RegexExtractor.extract(extracted_text, filename)
    if used_ocr:
        result.metodo_extraccion = "ocr"

    # Paso 4: Fallback opcional a LLM si regex quedó con advertencia o campos críticos vacíos
    if result.estado == "warning" and os.getenv("OPENAI_API_KEY"):
        llm_result = extract_with_llm(extracted_text, filename)
        if llm_result:
            return llm_result

    return result
