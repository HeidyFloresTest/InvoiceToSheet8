"""
Pruebas unitarias para la jerarquía de excepciones de dominio en extractor/exceptions.py.
Verifica herencia, códigos de error, serialización y mapeo en respuestas.
"""

import pytest

from extractor.exceptions import (
    CorruptedPdfError,
    InvalidInvoiceFormatError,
    InvoiceExtractionError,
    LlmFallbackError,
    OcrUnavailableError,
    PayloadTooLargeError,
)


def test_base_invoice_extraction_error():
    """Verifica que la excepción base serialice correctamente mensaje, código y detalles."""
    err = InvoiceExtractionError("Error genérico", code="CUSTOM_CODE", details={"line": 42})
    assert isinstance(err, Exception)
    assert err.message == "Error genérico"
    assert err.code == "CUSTOM_CODE"
    assert err.details == {"line": 42}

    d = err.to_dict()
    assert d["error_code"] == "CUSTOM_CODE"
    assert d["message"] == "Error genérico"
    assert d["details"]["line"] == 42


def test_corrupted_pdf_error_hierarchy():
    """Verifica herencia y valores por defecto de CorruptedPdfError."""
    err = CorruptedPdfError()
    assert isinstance(err, InvoiceExtractionError)
    assert err.code == "CORRUPTED_PDF"
    assert "corrupto" in err.message.lower()


def test_ocr_unavailable_error_hierarchy():
    """Verifica herencia y detalles de OcrUnavailableError."""
    err = OcrUnavailableError(details={"engine": "tesseract", "missing": "poppler"})
    assert isinstance(err, InvoiceExtractionError)
    assert err.code == "OCR_UNAVAILABLE"
    assert err.details["engine"] == "tesseract"


def test_llm_fallback_error_hierarchy():
    """Verifica herencia y código de LlmFallbackError."""
    err = LlmFallbackError(message="Límite de tokens excedido", details={"model": "gpt-4o-mini"})
    assert isinstance(err, InvoiceExtractionError)
    assert err.code == "LLM_FALLBACK_ERROR"
    assert err.message == "Límite de tokens excedido"


def test_invalid_invoice_format_error_hierarchy():
    """Verifica herencia y código de InvalidInvoiceFormatError."""
    err = InvalidInvoiceFormatError()
    assert isinstance(err, InvoiceExtractionError)
    assert err.code == "INVALID_FORMAT"


def test_payload_too_large_error_hierarchy():
    """Verifica herencia y código de PayloadTooLargeError."""
    err = PayloadTooLargeError()
    assert isinstance(err, InvoiceExtractionError)
    assert err.code == "PAYLOAD_TOO_LARGE"
    assert "25mb" in err.message.lower()


def test_raising_and_catching_typed_exceptions():
    """Verifica que atrapar InvoiceExtractionError capture todas las subclases del dominio."""
    with pytest.raises(InvoiceExtractionError) as exc_info:
        raise CorruptedPdfError("PDF ilegible")
    assert exc_info.value.code == "CORRUPTED_PDF"

    with pytest.raises(InvoiceExtractionError) as exc_info_ocr:
        raise OcrUnavailableError()
    assert exc_info_ocr.value.code == "OCR_UNAVAILABLE"


def test_api_exception_handler_serializes_error_detail(client):
    """Verifica que el exception handler de FastAPI mapee InvoiceExtractionError a ErrorDetail."""
    from extractor.exceptions import (
        InvoiceExtractionError,
        OcrUnavailableError,
        PayloadTooLargeError,
    )
    from main import app

    @app.get("/api/test-raise-invoice-error")
    async def route_raising_invoice_error():
        raise InvoiceExtractionError(
            "Fallo de prueba en extracción", code="TEST_EXTRACTION_ERR", details={"step": 1}
        )

    @app.get("/api/test-raise-payload-error")
    async def route_raising_payload_error():
        raise PayloadTooLargeError()

    @app.get("/api/test-raise-ocr-error")
    async def route_raising_ocr_error():
        raise OcrUnavailableError()

    res1 = client.get("/api/test-raise-invoice-error")
    assert res1.status_code == 400
    data1 = res1.json()
    assert data1["code"] == "TEST_EXTRACTION_ERR"
    assert data1["message"] == "Fallo de prueba en extracción"
    assert "timestamp" in data1
    assert data1["details"]["step"] == 1

    res2 = client.get("/api/test-raise-payload-error")
    assert res2.status_code == 413
    assert res2.json()["code"] == "PAYLOAD_TOO_LARGE"

    res3 = client.get("/api/test-raise-ocr-error")
    assert res3.status_code == 502
    assert res3.json()["code"] == "OCR_UNAVAILABLE"
