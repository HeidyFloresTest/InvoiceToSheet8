"""
Capa de Persistencia y ORM para InvoiceToSheet.
Utiliza SQLAlchemy con SQLite para registrar el histórico de facturas procesadas y auditoría.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings
from schemas import InvoiceData

# Ruta de la base de datos (inyección tipada vía Settings)
DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos ORM de la aplicación."""

    pass


class InvoiceRecord(Base):
    """Modelo ORM que representa una factura procesada en la base de datos."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero_factura = Column(String(100), nullable=True, index=True)
    fecha_emision = Column(String(50), nullable=True)
    nombre_proveedor = Column(String(255), nullable=True, index=True)
    id_fiscal_proveedor = Column(String(100), nullable=True, index=True)
    subtotal = Column(Float, nullable=True)
    impuestos = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    moneda = Column(String(10), default="USD")
    estado = Column(String(20), default="success", index=True)
    metodo_extraccion = Column(String(50), default="regex")
    nombre_archivo_origen = Column(String(255), nullable=True)
    mensaje_error = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def init_db() -> None:
    """Crea las tablas en la base de datos si no existen."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Generador de dependencias para sesiones de base de datos en endpoints FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class InvoiceRepository:
    """Repositorio para operaciones CRUD sobre facturas."""

    def __init__(self, db: Session):
        self.db = db

    def save_invoice(self, invoice: InvoiceData) -> InvoiceRecord:
        """Persiste una factura individual en la base de datos."""
        record = InvoiceRecord(
            numero_factura=invoice.numero_factura,
            fecha_emision=invoice.fecha_emision,
            nombre_proveedor=invoice.nombre_proveedor,
            id_fiscal_proveedor=invoice.id_fiscal_proveedor,
            subtotal=invoice.subtotal,
            impuestos=invoice.impuestos,
            total=invoice.total,
            moneda=invoice.moneda,
            estado=invoice.estado,
            metodo_extraccion=invoice.metodo_extraccion,
            nombre_archivo_origen=invoice.nombre_archivo_origen,
            mensaje_error=invoice.mensaje_error,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def save_batch(self, invoices: list[InvoiceData]) -> list[InvoiceRecord]:
        """Persiste un lote de facturas en una sola transacción."""
        records = [
            InvoiceRecord(
                numero_factura=inv.numero_factura,
                fecha_emision=inv.fecha_emision,
                nombre_proveedor=inv.nombre_proveedor,
                id_fiscal_proveedor=inv.id_fiscal_proveedor,
                subtotal=inv.subtotal,
                impuestos=inv.impuestos,
                total=inv.total,
                moneda=inv.moneda,
                estado=inv.estado,
                metodo_extraccion=inv.metodo_extraccion,
                nombre_archivo_origen=inv.nombre_archivo_origen,
                mensaje_error=inv.mensaje_error,
            )
            for inv in invoices
        ]
        self.db.add_all(records)
        self.db.commit()
        for r in records:
            self.db.refresh(r)
        return records

    def list_invoices(
        self, skip: int = 0, limit: int = 50, status: str | None = None
    ) -> list[InvoiceRecord]:
        """Obtiene un listado paginado de facturas registradas, con filtro opcional de estado."""
        query = self.db.query(InvoiceRecord)
        if status:
            query = query.filter(InvoiceRecord.estado == status)
        return query.order_by(InvoiceRecord.id.desc()).offset(skip).limit(limit).all()

    def get_by_id(self, invoice_id: int) -> InvoiceRecord | None:
        """Obtiene una factura por su ID primario."""
        return self.db.query(InvoiceRecord).filter(InvoiceRecord.id == invoice_id).first()

    def count_total(self, status: str | None = None) -> int:
        """Retorna el conteo total de facturas registradas, con filtro opcional de estado."""
        query = self.db.query(InvoiceRecord)
        if status:
            query = query.filter(InvoiceRecord.estado == status)
        return query.count()
