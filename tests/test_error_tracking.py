"""
Pruebas unitarias y de integración para el subsistema de rastreo de errores estructurados.
Verifica el buffer circular seguro para hilos, la agregación de métricas de errores
y los endpoints de auditoría operativa /api/errors/summary y /api/errors/recent.
"""

import pytest
from fastapi.testclient import TestClient

from extractor.exceptions import CorruptedPdfError
from observability import StructuredErrorTracker


@pytest.fixture
def clean_tracker():
    """Retorna una instancia aislada y limpia de StructuredErrorTracker."""
    tracker = StructuredErrorTracker(maxlen=5)
    tracker.clear()
    return tracker


def test_error_tracker_record_and_summary(clean_tracker):
    """Verifica el registro de errores y el cálculo correcto de métricas resumidas."""
    exc1 = CorruptedPdfError("PDF ilegible")
    clean_tracker.record_error(
        code=exc1.code,
        message=exc1.message,
        request_id="req-101",
        exc=exc1,
    )
    clean_tracker.record_error(
        code="INVALID_PAYLOAD",
        message="Payload inválido",
        request_id="req-102",
    )
    clean_tracker.record_error(
        code=exc1.code,
        message="Segundo PDF corrupto",
        request_id="req-103",
        exc=exc1,
    )

    summary = clean_tracker.get_summary()
    assert summary["total_recorded"] == 3
    assert summary["current_buffer_size"] == 3
    assert summary["counts_by_code"]["CORRUPTED_PDF"] == 2
    assert summary["counts_by_code"]["INVALID_PAYLOAD"] == 1
    assert summary["counts_by_type"]["CorruptedPdfError"] == 2


def test_error_tracker_circular_buffer_maxlen():
    """Verifica que el buffer circular descarte los elementos más antiguos al alcanzar maxlen."""
    tracker = StructuredErrorTracker(maxlen=3)
    for i in range(5):
        tracker.record_error(code=f"ERR_{i}", message=f"Mensaje {i}")

    summary = tracker.get_summary()
    assert summary["total_recorded"] == 5
    assert summary["current_buffer_size"] == 3

    recent = tracker.get_recent(limit=10)
    assert len(recent) == 3
    # Los más recientes deben ser ERR_4, ERR_3, ERR_2
    assert recent[0]["code"] == "ERR_4"
    assert recent[1]["code"] == "ERR_3"
    assert recent[2]["code"] == "ERR_2"


def test_error_tracker_filter_by_code(clean_tracker):
    """Verifica que el filtrado por código retorne únicamente los registros correspondientes."""
    clean_tracker.record_error(code="ERR_A", message="Error A1")
    clean_tracker.record_error(code="ERR_B", message="Error B1")
    clean_tracker.record_error(code="ERR_A", message="Error A2")

    filtered_a = clean_tracker.get_recent(code="ERR_A")
    assert len(filtered_a) == 2
    assert all(r["code"] == "ERR_A" for r in filtered_a)

    filtered_b = clean_tracker.get_recent(code="ERR_B")
    assert len(filtered_b) == 1
    assert filtered_b[0]["code"] == "ERR_B"


def test_api_error_endpoints_integration(client: TestClient):
    """Verifica la respuesta HTTP de /api/errors/summary y /api/errors/recent vía TestClient."""
    # Enviar un archivo con extensión no válida para provocar el registro del error
    response = client.post(
        "/api/extract",
        files=[("files", ("factura_invalida.txt", b"Texto plano", "text/plain"))],
    )
    assert response.status_code == 200
    batch_data = response.json()
    assert batch_data["total_con_error"] >= 1

    # Verificar que el error aparezca en el resumen
    summary_resp = client.get("/api/errors/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert "total_recorded" in summary_data
    assert "counts_by_code" in summary_data
    assert summary_data["total_recorded"] >= 1
    assert "INVALID_FORMAT" in summary_data["counts_by_code"]

    # Verificar que el error aparezca en la lista de recientes
    recent_resp = client.get("/api/errors/recent?limit=10")
    assert recent_resp.status_code == 200
    recent_data = recent_resp.json()
    assert isinstance(recent_data, list)
    assert len(recent_data) >= 1
    assert any(item["code"] == "INVALID_FORMAT" for item in recent_data)
