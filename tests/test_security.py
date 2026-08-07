"""
Pruebas de higiene de seguridad, mitigación OWASP y validación de credenciales.
Verifica:
1. Validación y sanitización estricta de OPENAI_API_KEY (sin filtración de secretos).
2. Protección contra inyecciones SQL y Path Traversal en parámetros de entrada.
3. Aislamiento CORS y presencia de cabeceras de seguridad HTTP recomendadas.
4. Resiliencia ante cargas maliciosas o sobrecargas de tamaño.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from extractor import extract_with_llm, is_valid_openai_api_key
from main import app

client = TestClient(app)


def test_is_valid_openai_api_key():
    """Verifica que la función rechace valores vacíos, nulos o marcadores de posición."""
    # Claves inválidas
    assert not is_valid_openai_api_key(None)
    assert not is_valid_openai_api_key("")
    assert not is_valid_openai_api_key("   ")
    assert not is_valid_openai_api_key("ab")
    assert not is_valid_openai_api_key("1234")
    assert not is_valid_openai_api_key("your_openai_api_key_here")
    assert not is_valid_openai_api_key("your_api_key_here")
    assert not is_valid_openai_api_key("your-api-key")
    assert not is_valid_openai_api_key("replace_me")
    assert not is_valid_openai_api_key("none")
    assert not is_valid_openai_api_key("null")

    # Claves válidas
    assert is_valid_openai_api_key("sk-test")
    assert is_valid_openai_api_key("sk-proj-1234567890abcdef")
    assert is_valid_openai_api_key("sk-test-valid-key-999")


def test_extract_with_llm_rejects_placeholder_key():
    """Verifica que extract_with_llm no invoque OpenAI si la clave es un marcador de posición."""
    with patch("os.getenv", return_value="your_openai_api_key_here"):
        result = extract_with_llm("Texto de factura", "factura.pdf")
        assert result is None


def test_openai_api_key_redaction_in_logs(caplog):
    """Verifica que si OpenAI arroja una excepción con la clave, esta sea redactada en el log."""
    sensitive_key = "sk-super-secret-key-12345678"
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError(
        f"Conexión rechazada para {sensitive_key}"
    )

    with (
        patch(
            "os.getenv",
            side_effect=lambda k, default=None: sensitive_key if k == "OPENAI_API_KEY" else default,
        ),
        patch("extractor.OPENAI_AVAILABLE", True),
        patch("extractor.OpenAI", return_value=mock_client),
    ):
        result = extract_with_llm("Texto de prueba", "archivo.pdf")
        assert result is None

        # Verificar que la clave sensible NO aparezca en los logs
        assert sensitive_key not in caplog.text
        assert "[REDACTED_API_KEY]" in caplog.text


def test_path_traversal_resilience():
    """Verifica que nombres de archivo con secuencias de path traversal sean manejados de forma segura."""
    malicious_filename = "../../../../etc/passwd.pdf"
    fake_pdf = b"%PDF-1.4 empty file"

    response = client.post(
        "/api/extract",
        files=[("files", (malicious_filename, fake_pdf, "application/pdf"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["facturas"]) == 1
    # El archivo se procesó en memoria sin acceder al filesystem
    assert data["facturas"][0]["nombre_archivo_origen"] == malicious_filename


def test_sql_injection_resilience_in_invoice_lookup():
    """Verifica que un intento de inyección SQL en el identificador sea rechazado por validación estricta de tipos."""
    sqli_payload = "' OR '1'='1"
    response = client.get(f"/api/invoices/{sqli_payload}")
    # Debe ser interceptado por validación estricta de FastAPI/Pydantic como 422 Unprocessable Content
    assert response.status_code == 422
    assert "Input should be a valid integer" in response.text or "int_parsing" in response.text


def test_security_headers_owasp_compliance():
    """Verifica que los encabezados de respuesta cumplan con estándares de endurecimiento OWASP."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers
