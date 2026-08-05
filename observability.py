"""
Módulo de Observabilidad y Monitoreo para InvoiceToSheet.
Proporciona:
- Logging estructurado con formato JSON y soporte para Correlation ID (Request ID).
- Métricas de rendimiento, tiempos de respuesta y conteo de transacciones.
- Manejo centralizado de excepciones con respuestas de error estandarizadas.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

# =====================================================================
# MODELOS DE OBSERVABILIDAD Y ERRORES
# =====================================================================


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Código de error estandarizado")
    message: str = Field(..., description="Mensaje explicativo del error")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: str | None = None
    details: dict[str, Any] | None = None


class SystemMetrics:
    """
    Registro en memoria de métricas operativas del microservicio.
    """

    def __init__(self):
        self.start_time: float = time.time()
        self.total_requests: int = 0
        self.total_invoices_processed: int = 0
        self.total_invoices_success: int = 0
        self.total_invoices_warning: int = 0
        self.total_invoices_error: int = 0
        self.total_excels_generated: int = 0
        self.total_errors: int = 0

    def record_request(self) -> None:
        self.total_requests += 1

    def record_invoices(self, success: int, warning: int, error: int) -> None:
        total = success + warning + error
        self.total_invoices_processed += total
        self.total_invoices_success += success
        self.total_invoices_warning += warning
        self.total_invoices_error += error

    def record_excel(self) -> None:
        self.total_excels_generated += 1

    def record_error(self) -> None:
        self.total_errors += 1

    def get_snapshot(self) -> dict[str, Any]:
        uptime_seconds = round(time.time() - self.start_time, 2)
        return {
            "uptime_seconds": uptime_seconds,
            "total_http_requests": self.total_requests,
            "invoices": {
                "total_processed": self.total_invoices_processed,
                "success": self.total_invoices_success,
                "warning": self.total_invoices_warning,
                "error": self.total_invoices_error,
                "success_rate_percent": (
                    round((self.total_invoices_success / self.total_invoices_processed) * 100, 2)
                    if self.total_invoices_processed > 0
                    else 100.0
                ),
            },
            "excels_generated": self.total_excels_generated,
            "total_unhandled_errors": self.total_errors,
        }

    def to_prometheus(self) -> str:
        """Exporta métricas operativas en formato estándar de texto de Prometheus (OpenMetrics)."""
        uptime = round(time.time() - self.start_time, 2)
        lines = [
            "# HELP invoicetosheet_http_requests_total Total de peticiones HTTP recibidas por el servicio.",
            "# TYPE invoicetosheet_http_requests_total counter",
            f"invoicetosheet_http_requests_total {self.total_requests}",
            "",
            "# HELP invoicetosheet_invoices_processed_total Total de facturas procesadas clasificadas por estado.",
            "# TYPE invoicetosheet_invoices_processed_total counter",
            f'invoicetosheet_invoices_processed_total{{status="success"}} {self.total_invoices_success}',
            f'invoicetosheet_invoices_processed_total{{status="warning"}} {self.total_invoices_warning}',
            f'invoicetosheet_invoices_processed_total{{status="error"}} {self.total_invoices_error}',
            "",
            "# HELP invoicetosheet_excels_generated_total Total de archivos Excel generados y exportados.",
            "# TYPE invoicetosheet_excels_generated_total counter",
            f"invoicetosheet_excels_generated_total {self.total_excels_generated}",
            "",
            "# HELP invoicetosheet_unhandled_errors_total Total de excepciones no controladas registradas.",
            "# TYPE invoicetosheet_unhandled_errors_total counter",
            f"invoicetosheet_unhandled_errors_total {self.total_errors}",
            "",
            "# HELP invoicetosheet_uptime_seconds Tiempo total de actividad del servicio en segundos.",
            "# TYPE invoicetosheet_uptime_seconds gauge",
            f"invoicetosheet_uptime_seconds {uptime}",
            "",
        ]
        return "\n".join(lines)


metrics = SystemMetrics()


# =====================================================================
# FORMATEADOR DE LOGS ESTRUCTURADOS (JSON)
# =====================================================================


class StructuredJsonFormatter(logging.Formatter):
    """Formatea cada registro de log como una cadena JSON estructurada."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_payload["request_id"] = record.request_id
        if hasattr(record, "extra_data"):
            log_payload["data"] = record.extra_data
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload, ensure_ascii=False)


def setup_logger(name: str = "InvoiceToSheet") -> logging.Logger:
    """Configura y retorna un logger estructurado."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
    return logger


logger = setup_logger()


# =====================================================================
# MIDDLEWARE DE REQUEST ID Y CABECERAS DE SEGURIDAD
# =====================================================================


class ObservabilityAndSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware que:
    1. Inyecta un Correlation ID (X-Request-ID) para trazabilidad en cada petición.
    2. Registra métricas de tiempo de procesamiento de cada request.
    3. Añade cabeceras de seguridad HTTP robustas (OWASP).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        metrics.record_request()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            metrics.record_error()
            logger.error(
                f"Excepción no controlada en {request.method} {request.url.path}: {exc}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            except Exception:
                pass
            raise exc

        process_time = round((time.time() - start_time) * 1000, 2)

        # Inyectar trazabilidad
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{process_time}ms"

        # Cabeceras de seguridad HTTP recomendadas
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Log de acceso para endpoints de API
        if request.url.path.startswith("/api"):
            logger.info(
                f"{request.method} {request.url.path} [{response.status_code}] {process_time}ms",
                extra={"request_id": request_id},
            )

        return response
