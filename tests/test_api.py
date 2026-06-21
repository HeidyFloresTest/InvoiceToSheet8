"""
Pruebas de integración HTTP para los endpoints de la API FastAPI.
"""


def test_health_check(client):
    """Verifica el endpoint de salud."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data


def test_metrics_endpoint(client):
    """Verifica el endpoint de telemetría y métricas operativas."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "invoices" in data
    assert "uptime_seconds" in data


def test_security_headers_present(client):
    """Verifica que el middleware inyecte Request ID y cabeceras de seguridad."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_extract_invoices_invalid_extension(client):
    """Verifica rechazo o marcado controlado de archivos no PDF."""
    files = [("files", ("archivo.txt", b"contenido no valido", "text/plain"))]
    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_archivos"] == 1
    assert data["total_con_error"] == 1
    assert data["facturas"][0]["estado"] == "error"


def test_extract_invoices_valid_pdf(client, sample_pdf_bytes):
    """Verifica procesamiento de un PDF válido en memoria."""
    files = [("files", ("factura_test.pdf", sample_pdf_bytes, "application/pdf"))]
    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_archivos"] == 1
    assert len(data["facturas"]) == 1


def test_export_excel_success(client, sample_invoice_list):
    """Verifica la generación y streaming binario del archivo Excel."""
    payload = {"facturas": [inv.model_dump() for inv in sample_invoice_list]}
    response = client.post("/api/export-excel", json=payload)
    assert response.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in response.headers["content-type"]
    )
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert len(response.content) > 1000


def test_export_excel_empty_payload(client):
    """Verifica error 400 si se envía lista vacía."""
    response = client.post("/api/export-excel", json={"facturas": []})
    assert response.status_code == 400
    assert "no hay facturas" in response.json()["detail"].lower()
