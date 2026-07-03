"""
Pruebas de integración simulada (Mocks) para la ruta de fallback con OCR.
Verifica que los PDFs escaneados o basados en imágenes activen el motor Tesseract/pdf2image sin requerir binarios externos.
"""

from unittest.mock import MagicMock, patch

from extractor import extract_invoice_from_pdf, extract_text_with_ocr


def test_extract_text_with_ocr_successful_mock():
    """Verifica que extract_text_with_ocr invoque convert_from_bytes e image_to_string."""
    mock_image = MagicMock()
    with (
        patch("extractor.convert_from_bytes", return_value=[mock_image]) as mock_convert,
        patch(
            "extractor.pytesseract.image_to_string",
            return_value="FACTURA OCR: F-OCR-999 TOTAL: 500.00",
        ) as mock_tess,
    ):
        result_text = extract_text_with_ocr(b"%PDF-mock")
        assert result_text is not None
        assert "FACTURA OCR" in result_text
        mock_convert.assert_called_once()
        mock_tess.assert_called_once_with(mock_image, lang="spa+eng")


def test_extract_invoice_triggers_ocr_fallback(low_text_pdf_bytes):
    """Verifica que un PDF sin texto digital invoque OCR y marque metodo_extraccion='ocr'."""
    mock_image = MagicMock()
    ocr_content = (
        "CONSULTORA DIGITAL SL\n"
        "NIF: B-12345678\n"
        "FACTURA: FAC-OCR-2024\n"
        "Fecha: 15/05/2024\n"
        "SUBTOTAL: 1000.00\n"
        "IVA 21%: 210.00\n"
        "TOTAL: 1210.00 EUR\n"
    )

    with (
        patch("extractor.OCR_AVAILABLE", True),
        patch("extractor.convert_from_bytes", return_value=[mock_image]),
        patch("extractor.pytesseract.image_to_string", return_value=ocr_content),
    ):
        invoice = extract_invoice_from_pdf(low_text_pdf_bytes, "escaneo_factura.pdf")

        assert invoice.estado == "success"
        assert invoice.metodo_extraccion == "ocr"
        assert invoice.numero_factura == "FAC-OCR-2024"
        assert invoice.total == 1210.00
        assert invoice.id_fiscal_proveedor == "B-12345678"


def test_extract_invoice_handles_ocr_exception(low_text_pdf_bytes):
    """Verifica que una falla o excepción en OCR no rompa el sistema y retorne estado 'error' controlado."""
    with (
        patch("extractor.OCR_AVAILABLE", True),
        patch("extractor.convert_from_bytes", side_effect=RuntimeError("Poppler no encontrado")),
    ):
        invoice = extract_invoice_from_pdf(low_text_pdf_bytes, "escaneo_roto.pdf")
        assert invoice.estado == "error"
        assert invoice.mensaje_error is not None
