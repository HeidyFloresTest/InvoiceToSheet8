"""
Jerarquía de excepciones tipadas para el dominio contable y pipeline de extracción.
Proporciona granularidad y códigos de error estandarizados para observabilidad.
"""


class InvoiceExtractionError(Exception):
    """Excepción base para todos los errores del pipeline de extracción de facturas."""

    def __init__(self, message: str, code: str = "EXTRACTION_ERROR", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        """Serializa la excepción para respuestas estructuradas de error."""
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
        }


class CorruptedPdfError(InvoiceExtractionError):
    """Se lanza cuando los bytes del PDF son inválidos o están corruptos."""

    def __init__(
        self, message: str = "El archivo PDF está corrupto o no contiene páginas legibles"
    ):
        super().__init__(message, code="CORRUPTED_PDF")


class OcrUnavailableError(InvoiceExtractionError):
    """Se lanza cuando el motor OCR (Tesseract / Poppler) no está disponible o falla."""

    def __init__(
        self,
        message: str = "El motor OCR no está disponible o falló en el procesamiento",
        details: dict | None = None,
    ):
        super().__init__(message, code="OCR_UNAVAILABLE", details=details)


class LlmFallbackError(InvoiceExtractionError):
    """Se lanza cuando el motor de fallback con LLM falla o rechaza la solicitud."""

    def __init__(
        self,
        message: str = "El motor de fallback con LLM no pudo estructurar los datos de la factura",
        details: dict | None = None,
    ):
        super().__init__(message, code="LLM_FALLBACK_ERROR", details=details)


class InvalidInvoiceFormatError(InvoiceExtractionError):
    """Se lanza cuando el formato o contenido no corresponde a una factura procesable."""

    def __init__(self, message: str = "Formato o estructura de factura no reconocible"):
        super().__init__(message, code="INVALID_FORMAT")


class PayloadTooLargeError(InvoiceExtractionError):
    """Se lanza cuando el archivo supera el límite permitido de 25MB."""

    def __init__(self, message: str = "El archivo excede el tamaño máximo permitido de 25MB"):
        super().__init__(message, code="PAYLOAD_TOO_LARGE")
