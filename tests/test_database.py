"""
Pruebas unitarias para la capa de persistencia ORM y repositorios de base de datos.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, InvoiceRecord, InvoiceRepository
from schemas import InvoiceData


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos SQLite en memoria aislada para cada test."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_save_and_get_invoice(db_session):
    """Verifica el guardado y recuperación de una factura individual mediante el repositorio."""
    repo = InvoiceRepository(db_session)
    invoice = InvoiceData(
        numero_factura="FAC-ORM-001",
        fecha_emision="2024-05-15",
        nombre_proveedor="Empresa Base de Datos S.A.",
        id_fiscal_proveedor="B12345678",
        subtotal=1000.0,
        impuestos=210.0,
        total=1210.0,
        moneda="EUR",
        nombre_archivo_origen="test_orm.pdf",
        estado="success",
        metodo_extraccion="regex",
    )

    record = repo.save_invoice(invoice)
    assert record.id is not None
    assert record.numero_factura == "FAC-ORM-001"
    assert record.total == 1210.0

    retrieved = repo.get_by_id(record.id)
    assert retrieved is not None
    assert retrieved.nombre_proveedor == "Empresa Base de Datos S.A."
    assert retrieved.id == record.id


def test_save_batch_and_list(db_session):
    """Verifica el guardado por lotes y la paginación de facturas."""
    repo = InvoiceRepository(db_session)
    invoices = [
        InvoiceData(
            numero_factura=f"BATCH-{i:03d}",
            fecha_emision="2024-05-16",
            nombre_proveedor=f"Proveedor {i}",
            id_fiscal_proveedor=f"RUT-{i}",
            subtotal=100.0 * i,
            impuestos=19.0 * i,
            total=119.0 * i,
            moneda="USD",
            nombre_archivo_origen=f"batch_{i}.pdf",
            estado="success",
        )
        for i in range(1, 6)
    ]

    records = repo.save_batch(invoices)
    assert len(records) == 5
    assert repo.count_total() == 5

    # Probar paginación
    page1 = repo.list_invoices(skip=0, limit=3)
    assert len(page1) == 3
    page2 = repo.list_invoices(skip=3, limit=3)
    assert len(page2) == 2


def test_get_nonexistent_invoice(db_session):
    """Verifica que buscar un ID inexistente retorne None."""
    repo = InvoiceRepository(db_session)
    assert repo.get_by_id(999999) is None
