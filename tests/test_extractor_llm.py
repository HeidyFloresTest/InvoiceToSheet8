"""
Pruebas de integración simulada (Mocks) para la ruta de fallback con LLM (OpenAI).
Verifica que las facturas no estructuradas o con advertencias invoquen el structured output de LLM.
"""

from unittest.mock import MagicMock, patch

from extractor import extract_invoice_from_pdf, extract_with_llm
from schemas import InvoiceData


def test_extract_with_llm_successful_mock():
    """Verifica que extract_with_llm invoque el endpoint de structured outputs de OpenAI."""
    mock_client = MagicMock()
    mock_parsed_invoice = InvoiceData(
        numero_factura="LLM-9901",
        fecha_emision="2024-06-01",
        nombre_proveedor="Proveedor IA S.A.S.",
        id_fiscal_proveedor="900123456-1",
        subtotal=800.0,
        impuestos=152.0,
        total=952.0,
        moneda="USD",
        nombre_archivo_origen="factura_compleja.pdf",
        estado="success",
        metodo_extraccion="llm",
    )

    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_parsed_invoice
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    with (
        patch(
            "os.getenv",
            side_effect=lambda k, default=None: (
                "fake-api-key" if k == "OPENAI_API_KEY" else default
            ),
        ),
        patch("extractor.OPENAI_AVAILABLE", True),
        patch("extractor.OpenAI", return_value=mock_client),
    ):
        result = extract_with_llm("Texto desordenado de factura", "factura_compleja.pdf")

        assert result is not None
        assert result.numero_factura == "LLM-9901"
        assert result.metodo_extraccion == "llm"
        assert result.total == 952.0


def test_pipeline_triggers_llm_on_warning_fallback(sample_pdf_bytes):
    """Verifica que si regex produce una advertencia y existe API Key, se invoque el fallback LLM."""
    mock_llm_invoice = InvoiceData(
        numero_factura="FOLIO-RECUPERADO",
        fecha_emision="2024-07-20",
        nombre_proveedor="Empresa Reestructurada",
        id_fiscal_proveedor="REC990101XYZ",
        subtotal=1500.0,
        impuestos=240.0,
        total=1740.0,
        moneda="MXN",
        nombre_archivo_origen="warning_invoice.pdf",
        estado="success",
        metodo_extraccion="llm",
    )

    with (
        patch(
            "os.getenv",
            side_effect=lambda k, default=None: (
                "fake-api-key" if k == "OPENAI_API_KEY" else default
            ),
        ),
        patch("extractor.extract_with_llm", return_value=mock_llm_invoice),
    ):
        # Simular resultado inicial en estado 'warning'
        invoice = extract_invoice_from_pdf(sample_pdf_bytes, "warning_invoice.pdf")
        assert invoice.numero_factura == "FOLIO-RECUPERADO"
        assert invoice.metodo_extraccion == "llm"
        assert invoice.estado == "success"


def test_extract_with_llm_returns_none_when_no_api_key():
    """Verifica que si OPENAI_API_KEY no está configurada, la función retorne None silenciosamente."""
    with patch("os.getenv", return_value=None):
        result = extract_with_llm("Texto de prueba", "test.pdf")
        assert result is None


def test_llm_fallback_sets_metodo_extraccion_field():
    """Verifica explícitamente que la extracción vía LLM establezca metodo_extraccion='llm'."""
    mock_client = MagicMock()
    mock_invoice = InvoiceData(
        numero_factura="INV-LLM-100",
        fecha_emision="2024-05-10",
        nombre_proveedor="Tech Solutions LLC",
        id_fiscal_proveedor="US99887766",
        subtotal=100.0,
        impuestos=16.0,
        total=116.0,
        moneda="USD",
        nombre_archivo_origen="scanned_receipt.pdf",
        estado="success",
        metodo_extraccion="llm",
    )
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_invoice
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    with (
        patch(
            "os.getenv",
            side_effect=lambda k, default=None: "sk-test" if k == "OPENAI_API_KEY" else default,
        ),
        patch("extractor.OPENAI_AVAILABLE", True),
        patch("extractor.OpenAI", return_value=mock_client),
    ):
        result = extract_with_llm("Receipt without clear regex patterns", "scanned_receipt.pdf")
        assert result is not None
        assert result.metodo_extraccion == "llm"
        assert result.estado == "success"
