"""
Modelos de datos y esquemas Pydantic para InvoiceToSheet.
Garantiza validación estricta de tipos tanto en la extracción como en la exportación a Excel.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class InvoiceData(BaseModel):
    """
    Representa la información estructurada extraída de una factura individual.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único para manipulación en el frontend",
    )
    numero_factura: str = Field(
        default="No identificado", description="Número de folio, comprobante o factura"
    )
    fecha_emision: str = Field(
        default="No identificada",
        description="Fecha de emisión normalizada (YYYY-MM-DD o texto detectado)",
    )
    nombre_proveedor: str = Field(
        default="No identificado", description="Razón social o nombre comercial del emisor"
    )
    id_fiscal_proveedor: str = Field(
        default="No identificado",
        description="Identificador tributario (RFC, RUT, NIF, CIF, RUC, etc.)",
    )
    nombre_cliente: str | None = Field(
        default=None, description="Razón social o nombre del receptor de la factura"
    )
    subtotal: float = Field(default=0.0, description="Base imponible o subtotal antes de impuestos")
    impuestos: float = Field(
        default=0.0,
        description="Monto acumulado de impuestos aplicados (IVA, VAT, retenciones, etc.)",
    )
    total: float = Field(default=0.0, description="Importe total a pagar de la factura")
    moneda: str = Field(
        default="USD", description="Código de moneda (USD, EUR, MXN, CLP, COP, PEN, etc.)"
    )
    nombre_archivo_origen: str = Field(..., description="Nombre del archivo PDF procesado")
    estado: Literal["success", "warning", "error"] = Field(
        default="success", description="Estado de procesamiento del documento"
    )
    mensaje_error: str | None = Field(
        default=None, description="Mensaje descriptivo en caso de error o advertencia"
    )
    metodo_extraccion: str = Field(
        default="regex", description="Método que extrajo la información (regex, ocr, llm, manual)"
    )


class BatchExtractResponse(BaseModel):
    """
    Respuesta consolidada del procesamiento por lotes de facturas.
    """

    total_archivos: int
    total_exitosos: int
    total_con_advertencia: int
    total_con_error: int
    facturas: list[InvoiceData]


class ExportExcelRequest(BaseModel):
    """
    Payload recibido por el endpoint de exportación a Excel.
    Permite enviar las facturas revisadas o editadas por el usuario en el frontend.
    """

    facturas: list[InvoiceData]


class InvoiceHistoryItem(BaseModel):
    """Representa una factura histórica almacenada en la base de datos."""

    id: int
    numero_factura: str | None = None
    fecha_emision: str | None = None
    nombre_proveedor: str | None = None
    id_fiscal_proveedor: str | None = None
    subtotal: float | None = 0.0
    impuestos: float | None = 0.0
    total: float | None = 0.0
    moneda: str = "USD"
    estado: str = "success"
    metodo_extraccion: str = "regex"
    nombre_archivo_origen: str | None = None
    mensaje_error: str | None = None

    class Config:
        from_attributes = True


class InvoiceHistoryResponse(BaseModel):
    """Respuesta con el listado paginado del historial de facturas."""

    total: int
    skip: int
    limit: int
    invoices: list[InvoiceHistoryItem]
