"""
Pipeline principal de extracción de facturas para InvoiceToSheet.
Orquesta pdfplumber, fallback OCR (pytesseract), motor de reglas Regex y fallback LLM.
"""

import io
import logging
import os

import pdfplumber

from extractor import llm as llm_module
from extractor import ocr as ocr_module
from extractor.engine import RegexExtractor
from schemas import InvoiceData

logger = logging.getLogger("InvoiceExtractor.Pipeline")


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
            mensaje_error="El archivo está vacío (0 bytes).",
        )

    extracted_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
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
                mensaje_error="El archivo PDF está protegido con contraseña.",
            )
        pass

    # Si no se extrajo suficiente texto (posible PDF escaneado / imagen)
    used_ocr = False
    if len(extracted_text) < 40:
        ocr_text = ocr_module.extract_text_with_ocr(pdf_bytes)
        if ocr_text and len(ocr_text.strip()) > 30:
            extracted_text = ocr_text.strip()
            used_ocr = True

    # Si aún no hay texto tras intentar OCR
    if not extracted_text or len(extracted_text.strip()) < 15:
        return InvoiceData(
            nombre_archivo_origen=filename,
            estado="error",
            mensaje_error="No se pudo extraer texto. Es posible que sea un escaneo sin OCR o un archivo dañado.",
        )

    # Paso 3: Extracción vía Reglas y Heurísticas
    result = RegexExtractor.extract(extracted_text, filename)
    if used_ocr:
        result.metodo_extraccion = "ocr"

    # Paso 4: Fallback opcional a LLM si regex quedó con advertencia o campos críticos vacíos
    if result.estado == "warning" and os.getenv("OPENAI_API_KEY"):
        llm_result = llm_module.extract_with_llm(extracted_text, filename)
        if llm_result:
            return llm_result

    return result
