"""
Motor de extracción de facturas basado en expresiones regulares y heurísticas contables.
Optimizado para formatos hispanohablantes (México, España, Chile, Colombia, Perú, Argentina, Brasil)
e internacionales (Estados Unidos, Reino Unido, Unión Europea).
"""

import re
from typing import Literal

from extractor.normalizers import normalize_amount, normalize_date
from schemas import InvoiceData


class RegexExtractor:
    """
    Extractor de alta velocidad y tolerancia para facturas usando expresiones regulares.
    """

    PATTERNS_INVOICE_NUMBER = [
        r"(?:factura|invoice|folio|comprobante|recibo|rechnung|bill\s*no\.?)\s*(?:n[º°o#\.]?|n[uú]mero|nr\.?)?\s*[:#\-\s]*([A-Z0-9][A-Z0-9\-_/]{1,25})\b",
        r"\b(?:n[º°o#\.]|n[uú]mero|folio|nr\.?)\s*[:#\-\s]*([A-Z0-9][A-Z0-9\-_/]{1,25})\b",
        r"\b([A-Z]{1,3}-\d{4,10}(?:-\d{1,6})?)\b",
    ]

    PATTERNS_DATES = [
        r"(?:fecha\s*(?:de)?\s*(?:emisi[oó]n|expedici[oó]n|factura)?|date|emisi[oó]n)\s*[:#\-\s]*([0-9]{1,2}[-/\.][0-9]{1,2}[-/\.][0-9]{2,4})",
        r"(?:fecha\s*(?:de)?\s*(?:emisi[oó]n|expedici[oó]n|factura)?|date|emisi[oó]n)\s*[:#\-\s]*([0-9]{4}[-/\.][0-9]{1,2}[-/\.][0-9]{1,2})",
        r"(?:fecha|emisi[oó]n)\s*[:#\-\s]*([0-9]{1,2}\s*(?:de)?\s*[A-Za-z]{3,10}\s*(?:de)?\s*[0-9]{4})",
    ]

    PATTERNS_TAX_ID = {
        "RFC": r"\b([A-Z&Ñ]{3,4}\s*-?\s*\d{6}\s*-?\s*[A-Z0-9]{3})\b",
        "RUT": r"\b(\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK])\b",
        "NIF_CIF": r"\b([A-HJ-NP-SUVW]-?\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]-?\d{7}[A-Z])\b",
        "RUC": r"\b((?:10|15|17|20)\d{9}|\d{13})\b",
        "CHE": r"\b(CHE[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3}(?:\s*(?:MWST|TVA|IVA))?)\b",
        "GENERIC": r"(?:R\.?F\.?C\.?|R\.?U\.?T\.?|N\.?I\.?F\.?|C\.?I\.?F\.?|R\.?U\.?C\.?|NIT|Tax\s*ID|VAT\s*(?:No|ID)?|UID|CHE)\s*[:#\-\s]*([A-Z0-9\.\-]{6,20})\b",
    }

    # Patrón base reutilizable para capturar importes monetarios en diversos formatos internacionales
    _AMOUNT_REGEX = r"([$€£¥R\$\sS/\.CHF]*(?:[0-9]{1,3}(?:[.,\s][0-9]{3})+(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?))"

    PATTERNS_TOTAL = [
        rf"(?:total\s*(?:a\s*pagar|general|factura|comprobante)?|importe\s*total|grand\s*total|monto\s*total|gesamtbetrag)\s*[:=]?\s*{_AMOUNT_REGEX}",
        rf"(?:\bTOTAL\b)\s*[:=]?\s*{_AMOUNT_REGEX}",
    ]

    PATTERNS_SUBTOTAL = [
        rf"(?:subtotal|sub-total|sub\s*total|base\s*imponible|base\s*gravada|importe\s*neto|neto|nettobetrag)\s*[:=]?\s*{_AMOUNT_REGEX}",
        rf"(?:\bSUBTOTAL\b)\s*[:=]?\s*{_AMOUNT_REGEX}",
    ]

    PATTERNS_TAXES = [
        rf"(?:i\.?v\.?a\.?|impuesto(?:s)?|vat|igv|tax|mwst|tva)\s*(?:\(?\d{1, 2}(?:\.\d)?%?\)?\s*)?[:=]?\s*{_AMOUNT_REGEX}",
        rf"(?:16%|21%|20%|19%|18%|8\.1%|7\.7%|10%)\s*[:=]?\s*{_AMOUNT_REGEX}",
    ]

    CURRENCY_INDICATORS = {
        "MXN": ["MXN", "PESOS MEXICANOS", "M.N."],
        "EUR": ["EUR", "€", "EUROS"],
        "USD": ["USD", "US$", "DOLARES", "DOLLARS"],
        "CLP": ["CLP", "PESOS CHILENOS"],
        "COP": ["COP", "PESOS COLOMBIANOS"],
        "PEN": ["PEN", "S/.", "SOLES"],
        "ARS": ["ARS", "PESOS ARGENTINOS"],
        "BRL": ["BRL", "R$", "REAIS", "REALES"],
        "GBP": ["GBP", "£", "POUNDS", "LIBRAS"],
        "CHF": ["CHF", "FRANCOS SUIZOS", "SWISS FRANCS"],
        "JPY": ["JPY", "¥", "YEN", "YENES"],
        "CAD": ["CAD", "C$", "CANADIAN DOLLARS"],
        "AUD": ["AUD", "A$", "AUSTRALIAN DOLLARS"],
    }

    @classmethod
    def _extract_amount_from_patterns(cls, text: str, patterns: list[str]) -> float:
        """Extrae y normaliza el último importe monetario válido coincidente con una lista de patrones regex."""
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                val = normalize_amount(matches[-1].group(1))
                if val > 0:
                    return val
        return 0.0

    @classmethod
    def _search_first_valid_pattern(
        cls, text: str, patterns: list[str], excluded: set[str] | None = None
    ) -> str | None:
        """Busca el primer patrón coincidente y retorna el primer grupo de captura filtrando exclusiones."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if not candidate:
                    continue
                if excluded and candidate.lower() in excluded:
                    continue
                return candidate
        return None

    @classmethod
    def extract(cls, text: str, filename: str) -> InvoiceData:
        """
        Ejecuta la extracción de datos sobre el texto plano extraído del PDF.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Número de Factura
        num_factura = (
            cls._search_first_valid_pattern(
                text,
                cls.PATTERNS_INVOICE_NUMBER,
                excluded={"de", "del", "fecha", "cliente", "total"},
            )
            or "No identificado"
        )

        # 2. Fecha de Emisión
        raw_date = cls._search_first_valid_pattern(text, cls.PATTERNS_DATES) or "No identificada"
        fecha_emision = normalize_date(raw_date)

        # 3. ID Fiscal del Proveedor (Emisor)
        id_fiscal = cls._search_first_valid_pattern(text, [cls.PATTERNS_TAX_ID["GENERIC"]])
        if not id_fiscal:
            tax_patterns = [cls.PATTERNS_TAX_ID[k] for k in ["RFC", "NIF_CIF", "RUC", "RUT"]]
            id_fiscal = cls._search_first_valid_pattern(text, tax_patterns) or "No identificado"

        # 4. Nombre del Proveedor (Emisor)
        nombre_proveedor = "No identificado"
        prov_match = re.search(
            r"(?:emisor|de|proveedor|vendedor|raz[oó]n\s*social|empresa|company)\s*[:\-]\s*([^\n\r,]{3,60})",
            text,
            re.IGNORECASE,
        )
        if prov_match:
            candidate = prov_match.group(1).strip()
            if not any(
                k in candidate.lower() for k in ["factura", "cliente", "fecha", "rfc", "nif"]
            ):
                nombre_proveedor = candidate

        if nombre_proveedor == "No identificado" and lines:
            for line_item in lines[:5]:
                if re.search(
                    r"\b(S\.?A\.?|S\.?L\.?|S\.?A\.?S\.?|S\.?R\.?L\.?|C\.?V\.?|LLC|INC|CORP|GMBH|S\.?C\.?)\b",
                    line_item,
                    re.IGNORECASE,
                ):
                    nombre_proveedor = line_item
                    break
            if (
                nombre_proveedor == "No identificado"
                and len(lines[0]) > 3
                and not re.search(r"(factura|invoice|folio|\d{4})", lines[0], re.IGNORECASE)
            ):
                nombre_proveedor = lines[0][:60]

        # 5. Nombre del Cliente (Receptor)
        nombre_cliente = None
        cliente_match = re.search(
            r"(?:cliente|receptor|facturado\s*a|billed\s*to|para|customer|se[ñn]or(?:es)?)\s*[:\-]\s*([^\n\r,]{3,60})",
            text,
            re.IGNORECASE,
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

        if not found_currency and "RFC" in text.upper():
            moneda = "MXN"
        elif not found_currency and ("€" in text or "EUR" in text.upper()):
            moneda = "EUR"

        # 7. Subtotal, Impuestos y Total (extracción modular unificada)
        total_val = cls._extract_amount_from_patterns(text, cls.PATTERNS_TOTAL)
        subtotal_val = cls._extract_amount_from_patterns(text, cls.PATTERNS_SUBTOTAL)
        impuestos_val = cls._extract_amount_from_patterns(text, cls.PATTERNS_TAXES)

        # Reconciliación matemática básica
        if subtotal_val > 0 and total_val > 0 and impuestos_val == 0.0:
            if total_val > subtotal_val:
                impuestos_val = round(total_val - subtotal_val, 2)
        elif total_val == 0.0 and (subtotal_val > 0 or impuestos_val > 0):
            total_val = round(subtotal_val + impuestos_val, 2)
        elif total_val > 0 and subtotal_val == 0.0 and impuestos_val > 0:
            subtotal_val = round(total_val - impuestos_val, 2)

        # Determinar estado
        estado: Literal["success", "warning", "error"] = "success"
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
            metodo_extraccion="regex",
        )
