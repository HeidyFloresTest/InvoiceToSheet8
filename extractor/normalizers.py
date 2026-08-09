"""
Utilidades de normalización matemática y temporal para InvoiceToSheet.
Proporciona parsing tolerante de importes monetarios y fechas internacionales.
"""

import re
from datetime import datetime


def normalize_amount(raw_val: str | None) -> float:
    """
    Normaliza representaciones numéricas monetarias complejas a float.
    Maneja:
      - '1,234.50' (formato US/UK)
      - '1.234,50' (formato hispano/europeo)
      - '1234,50' y '1234.50'
      - Espacios y símbolos de divisas ($ 1 234,50 / R$ 4.500,75)
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
        if len(parts) > 2:
            # Múltiples separadores de miles (ej. 1.500.000)
            cleaned = cleaned.replace(".", "")
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
            # Formatos monetarios sin decimales (común en CLP, COP, PYG: ej. 150.000 -> 150000)
            cleaned = cleaned.replace(".", "")

    try:
        return round(float(cleaned), 2)
    except (ValueError, TypeError):
        return 0.0


def normalize_date(raw_date: str | None) -> str:
    """
    Normaliza fechas variadas al estándar ISO (YYYY-MM-DD).
    Soporta formatos numéricos y textuales (en español e inglés).
    """
    if not raw_date:
        return "No identificada"

    raw_date = raw_date.strip()

    # Mapeo de meses en español e inglés
    meses = {
        "enero": "01",
        "ene": "01",
        "january": "01",
        "jan": "01",
        "febrero": "02",
        "feb": "02",
        "february": "02",
        "marzo": "03",
        "mar": "03",
        "march": "03",
        "abril": "04",
        "abr": "04",
        "april": "04",
        "apr": "04",
        "mayo": "05",
        "may": "05",
        "junio": "06",
        "jun": "06",
        "june": "06",
        "julio": "07",
        "jul": "07",
        "july": "07",
        "agosto": "08",
        "ago": "08",
        "august": "08",
        "aug": "08",
        "septiembre": "09",
        "sep": "09",
        "setiembre": "09",
        "september": "09",
        "octubre": "10",
        "oct": "10",
        "october": "10",
        "noviembre": "11",
        "nov": "11",
        "november": "11",
        "diciembre": "12",
        "dic": "12",
        "december": "12",
        "dec": "12",
    }

    # Caso 1: Fechas con texto ("15 de enero de 2024", "22 de Octubre del 2023" o "15 Jan 2024")
    text_match = re.search(
        r"(\d{1,2})\s*(?:de|\/|-)?\s*([A-Za-z]{3,10})\s*(?:de|del|\/|-|,)?\s*(\d{4})",
        raw_date,
        re.IGNORECASE,
    )
    if text_match:
        dia, mes_str, anio = text_match.groups()
        mes_key = mes_str.lower()
        if mes_key in meses:
            return f"{anio}-{meses[mes_key]}-{int(dia):02d}"

    # Caso 2: Formatos numéricos DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY/MM/DD
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y"]

    candidate = re.search(r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4})\b", raw_date)
    date_to_test = candidate.group(1) if candidate else raw_date

    for fmt in formatos:
        try:
            dt = datetime.strptime(date_to_test, fmt)
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return raw_date[:25]
