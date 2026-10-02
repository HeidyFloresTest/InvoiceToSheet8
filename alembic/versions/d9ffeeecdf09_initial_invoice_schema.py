"""initial_invoice_schema

Revision ID: d9ffeeecdf09
Revises:
Create Date: 2026-10-27 10:51:52.746390

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9ffeeecdf09"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create invoices table."""
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("numero_factura", sa.String(length=100), nullable=True),
        sa.Column("fecha_emision", sa.String(length=50), nullable=True),
        sa.Column("nombre_proveedor", sa.String(length=255), nullable=True),
        sa.Column("id_fiscal_proveedor", sa.String(length=100), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=True),
        sa.Column("impuestos", sa.Float(), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("moneda", sa.String(length=10), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=True),
        sa.Column("metodo_extraccion", sa.String(length=50), nullable=True),
        sa.Column("nombre_archivo_origen", sa.String(length=255), nullable=True),
        sa.Column("mensaje_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)
    op.create_index(
        op.f("ix_invoices_numero_factura"), "invoices", ["numero_factura"], unique=False
    )
    op.create_index(
        op.f("ix_invoices_nombre_proveedor"), "invoices", ["nombre_proveedor"], unique=False
    )
    op.create_index(
        op.f("ix_invoices_id_fiscal_proveedor"), "invoices", ["id_fiscal_proveedor"], unique=False
    )
    op.create_index(op.f("ix_invoices_estado"), "invoices", ["estado"], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop invoices table."""
    op.drop_index(op.f("ix_invoices_estado"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_id_fiscal_proveedor"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_nombre_proveedor"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_numero_factura"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_id"), table_name="invoices")
    op.drop_table("invoices")
