"""
Pruebas para el módulo de observabilidad, métricas y formato de logs estructurados.
"""

import json
import logging

from observability import StructuredJsonFormatter, SystemMetrics


def test_system_metrics_counters():
    """Verifica el cálculo de tasas y métricas operativas."""
    metrics = SystemMetrics()
    metrics.record_request()
    metrics.record_request()
    metrics.record_invoices(success=2, warning=1, error=1)
    metrics.record_excel()

    snapshot = metrics.get_snapshot()
    assert snapshot["total_http_requests"] == 2
    assert snapshot["invoices"]["total_processed"] == 4
    assert snapshot["invoices"]["success"] == 2
    assert snapshot["invoices"]["warning"] == 1
    assert snapshot["invoices"]["error"] == 1
    assert snapshot["invoices"]["success_rate_percent"] == 50.0
    assert snapshot["excels_generated"] == 1
    assert snapshot["uptime_seconds"] >= 0


def test_structured_json_formatter():
    """Verifica que el formateador genere JSON válido con metadatos."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Operación completada exitosamente",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    formatted = formatter.format(record)

    data = json.loads(formatted)
    assert data["level"] == "INFO"
    assert data["message"] == "Operación completada exitosamente"
    assert data["request_id"] == "req-12345"
    assert "timestamp" in data


def test_prometheus_metrics_format():
    """Verifica la generación del formato de texto plano compatible con Prometheus / OpenMetrics."""
    metrics = SystemMetrics()
    metrics.record_request()
    metrics.record_invoices(success=5, warning=2, error=1)
    metrics.record_excel()
    metrics.record_error()

    prom_text = metrics.to_prometheus()

    assert "# HELP invoicetosheet_http_requests_total" in prom_text
    assert "# TYPE invoicetosheet_http_requests_total counter" in prom_text
    assert "invoicetosheet_http_requests_total 1" in prom_text

    assert "# TYPE invoicetosheet_invoices_processed_total counter" in prom_text
    assert 'invoicetosheet_invoices_processed_total{status="success"} 5' in prom_text
    assert 'invoicetosheet_invoices_processed_total{status="warning"} 2' in prom_text
    assert 'invoicetosheet_invoices_processed_total{status="error"} 1' in prom_text

    assert "invoicetosheet_excels_generated_total 1" in prom_text
    assert "invoicetosheet_unhandled_errors_total 1" in prom_text
    assert "# TYPE invoicetosheet_uptime_seconds gauge" in prom_text
    assert "invoicetosheet_uptime_seconds" in prom_text
