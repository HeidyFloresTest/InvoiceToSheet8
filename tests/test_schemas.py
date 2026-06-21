"""
Pruebas unitarias para esquemas Pydantic y validación estricta de datos.
"""

import pytest
from pydantic import ValidationError

from schemas import BatchExtractResponse, ExportExcelRequest, InvoiceData


def test_invoice_data_defaults():
    """Valida los valores por defecto del esquema InvoiceData."""
    inv = InvoiceData(nombre_archivo_origen="prueba.pdf")
    assert inv.numero_factura == "No identificado"
    assert inv.fecha_emision == "No identificada"
    assert inv.nombre_proveedor == "No identificado"
    assert inv.id_fiscal_proveedor == "No identificado"
    assert inv.subtotal == 0.0
    assert inv.impuestos == 0.0
    assert inv.total == 0.0
    assert inv.moneda == "USD"
    assert inv.estado == "success"
    assert inv.id is not None


def test_invoice_data_custom_values():
    """Valida asignación explícita de campos y tipado."""
    inv = InvoiceData(
        numero_factura="F-1234",
        fecha_emision="2024-05-10",
        nombre_proveedor="Empresa Alfa",
        id_fiscal_proveedor="RFC123456789",
        nombre_cliente="Cliente Beta",
        subtotal=100.50,
        impuestos=16.08,
        total=116.58,
        moneda="MXN",
        nombre_archivo_origen="factura.pdf",
        estado="warning",
        metodo_extraccion="ocr",
    )
    assert inv.total == 116.58
    assert inv.moneda == "MXN"
    assert inv.metodo_extraccion == "ocr"


def test_invoice_data_missing_required_filename():
    """Valida que nombre_archivo_origen sea obligatorio."""
    with pytest.raises(ValidationError):
        InvoiceData()


def test_batch_extract_response():
    """Valida el cálculo y estructura de la respuesta en lote."""
    inv1 = InvoiceData(nombre_archivo_origen="f1.pdf", estado="success")
    inv2 = InvoiceData(nombre_archivo_origen="f2.pdf", estado="error")

    resp = BatchExtractResponse(
        total_archivos=2,
        total_exitosos=1,
        total_con_advertencia=0,
        total_con_error=1,
        facturas=[inv1, inv2],
    )
    assert resp.total_archivos == 2
    assert len(resp.facturas) == 2


def test_export_excel_request():
    """Valida el payload de exportación a Excel."""
    inv = InvoiceData(nombre_archivo_origen="export.pdf")
    req = ExportExcelRequest(facturas=[inv])
    assert len(req.facturas) == 1
