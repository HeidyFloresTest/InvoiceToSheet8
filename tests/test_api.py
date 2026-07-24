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


def test_cors_preflight_and_allowed_origin(client):
    """Verifica que un origen permitido reciba cabeceras CORS de acceso."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/extract", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_disallowed_origin(client):
    """Verifica que orígenes no autorizados no reciban cabecera access-control-allow-origin."""
    headers = {
        "Origin": "http://malicious-site.example.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/extract", headers=headers)
    assert (
        response.headers.get("access-control-allow-origin") != "http://malicious-site.example.com"
    )


def test_extract_invoices_corrupted_pdf(client):
    """Verifica que un archivo PDF corrupto sea manejado grácilmente retornando estado error."""
    corrupted_content = b"%PDF-1.4 CORRUPTED DATA NOT VALID PDF CONTENT \x00\xff\xee"
    files = [("files", ("factura_corrupta.pdf", corrupted_content, "application/pdf"))]
    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_archivos"] == 1
    assert data["total_con_error"] == 1
    factura = data["facturas"][0]
    assert factura["estado"] == "error"
    assert factura["nombre_archivo_origen"] == "factura_corrupta.pdf"
    assert (
        "error" in factura["mensaje_error"].lower() or "dañado" in factura["mensaje_error"].lower()
    )


def test_extract_invoices_oversized_file(client):
    """Verifica que un archivo que excede los 25MB sea rechazado grácilmente por tamaño."""
    oversized_size = 25 * 1024 * 1024 + 1024  # 25MB + 1KB
    # Usar un buffer simulado sin consumir memoria innecesaria
    oversized_content = b"0" * oversized_size
    files = [("files", ("factura_gigante.pdf", oversized_content, "application/pdf"))]
    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_archivos"] == 1
    assert data["total_con_error"] == 1
    factura = data["facturas"][0]
    assert factura["estado"] == "error"
    assert "excede el tamaño máximo" in factura["mensaje_error"]


def test_get_invoice_history_and_by_id(client, sample_pdf_bytes):
    """Verifica la consulta del historial paginado y búsqueda por ID en la base de datos."""
    # Extraer factura para poblar la base de datos
    files = [("files", ("factura_para_historial.pdf", sample_pdf_bytes, "application/pdf"))]
    res_extract = client.post("/api/extract", files=files)
    assert res_extract.status_code == 200

    # Consultar historial
    res_history = client.get("/api/invoices/history?skip=0&limit=10")
    assert res_history.status_code == 200
    history_data = res_history.json()
    assert "total" in history_data
    assert "invoices" in history_data
    assert history_data["total"] >= 1

    first_item = history_data["invoices"][0]
    inv_id = first_item["id"]

    # Consultar por ID
    res_single = client.get(f"/api/invoices/{inv_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == inv_id

    # Consultar ID inexistente -> 404
    res_404 = client.get("/api/invoices/99999999")
    assert res_404.status_code == 404
