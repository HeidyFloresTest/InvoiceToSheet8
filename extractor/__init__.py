"""
Paquete modular de extracción de facturas para InvoiceToSheet.
Proporciona normalizadores, integración OCR, fallback LLM estructurado y motor regex.
"""

from extractor.engine import RegexExtractor
from extractor.llm import (
    OPENAI_AVAILABLE,
    OpenAI,
    extract_with_llm,
    is_valid_openai_api_key,
)
from extractor.normalizers import normalize_amount, normalize_date
from extractor.ocr import (
    OCR_AVAILABLE,
    convert_from_bytes,
    extract_text_with_ocr,
    pytesseract,
)
from extractor.pipeline import extract_invoice_from_pdf

__all__ = [
    "RegexExtractor",
    "extract_invoice_from_pdf",
    "normalize_amount",
    "normalize_date",
    "extract_text_with_ocr",
    "extract_with_llm",
    "is_valid_openai_api_key",
    "OCR_AVAILABLE",
    "OPENAI_AVAILABLE",
    "OpenAI",
    "pytesseract",
    "convert_from_bytes",
]
