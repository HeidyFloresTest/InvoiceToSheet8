"""
Módulo de OCR con Pytesseract para InvoiceToSheet.
Proporciona extracción de texto para PDFs escaneados o basados en imagen.
"""

import logging
import os

logger = logging.getLogger("InvoiceExtractor.OCR")

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image, ImageEnhance, ImageOps

    OCR_AVAILABLE = True
    tess_path = os.getenv("TESSERACT_PATH")
    if tess_path and os.path.exists(tess_path):
        pytesseract.pytesseract.tesseract_cmd = tess_path
except ImportError:
    pytesseract = None  # type: ignore
    convert_from_bytes = None  # type: ignore
    Image = None  # type: ignore
    OCR_AVAILABLE = False


def preprocess_image_for_ocr(img: "Image.Image") -> "Image.Image":
    """
    Mejora el contraste y legibilidad de imágenes antes de ejecutar el OCR:
    - Convierte a escala de grises (modo 'L').
    - Aplica autocontraste para normalizar histogramas de fondo y texto.
    - Incrementa el contraste dinámico para separar caracteres tenues.
    """
    try:
        gray = img.convert("L")
        contrasted = ImageOps.autocontrast(gray, cutoff=2)
        enhancer = ImageEnhance.Contrast(contrasted)
        return enhancer.enhance(1.4)
    except Exception as e:
        logger.debug(f"Preprocesamiento omitido por error: {e}")
        return img


def extract_text_with_ocr(pdf_bytes: bytes) -> str | None:
    """
    Convierte las primeras páginas del PDF en imágenes, aplica preprocesamiento y extrae texto vía pytesseract.
    """
    if not OCR_AVAILABLE:
        logger.warning("pytesseract o pdf2image no están disponibles en el entorno.")
        return None

    try:
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=2)
        full_ocr_text = []
        for img in images:
            preprocessed = preprocess_image_for_ocr(img)
            text = pytesseract.image_to_string(preprocessed, lang="spa+eng")
            full_ocr_text.append(text)
        return "\n".join(full_ocr_text)
    except Exception as e:
        logger.error(f"Error durante la ejecución del OCR: {e}")
        return None
