"""
Configuración de fixtures reutilizables para la suite de pruebas Pytest.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from schemas import InvoiceData


@pytest.fixture
def client():
    """Cliente de pruebas para interactuar con la API FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_invoice_data():
    """Factura de prueba con valores válidos y coherentes."""
    return InvoiceData(
        numero_factura="FAC-2024-001",
        fecha_emision="2024-03-15",
        nombre_proveedor="ACME Corporation S.A.",
        id_fiscal_proveedor="B-12345678",
        nombre_cliente="Cliente Global S.L.",
        subtotal=1000.00,
        impuestos=210.00,
        total=1210.00,
        moneda="EUR",
        nombre_archivo_origen="factura_acme.pdf",
        estado="success",
        metodo_extraccion="regex",
    )


@pytest.fixture
def sample_invoice_list(sample_invoice_data):
    """Lista de facturas con diferentes estados y monedas."""
    invoice_2 = InvoiceData(
        numero_factura="INV-9982",
        fecha_emision="2024-04-10",
        nombre_proveedor="Tech Services LLC",
        id_fiscal_proveedor="12-3456789",
        nombre_cliente="Empresa Receptora",
        subtotal=2500.00,
        impuestos=400.00,
        total=2900.00,
        moneda="USD",
        nombre_archivo_origen="tech_services.pdf",
        estado="warning",
        mensaje_error="Revisar número de factura",
        metodo_extraccion="regex",
    )
    return [sample_invoice_data, invoice_2]


@pytest.fixture
def sample_pdf_bytes():
    """Genera bytes de un PDF mínimo válido en memoria."""
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 44 >> stream\n"
        b"BT /F1 12 Tf 72 712 Td (FACTURA N: TEST-001) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000206 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n300\n%%EOF\n"
    )
    return content
