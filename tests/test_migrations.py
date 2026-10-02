"""
Pruebas automatizadas de migraciones de base de datos con Alembic.
Verifica que las operaciones de upgrade y downgrade se ejecuten sin errores
y garanticen la integridad del esquema relacional.
"""

import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, pool

from alembic import command


@pytest.fixture
def temp_alembic_db():
    """Genera una base de datos SQLite temporal y la configuración de Alembic correspondiente."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_migration.db"
    db_url = f"sqlite:///{db_path}"

    root_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = root_dir / "alembic.ini"

    config = Config(str(alembic_ini_path))
    config.set_main_option("sqlalchemy.url", db_url)
    config.set_main_option("script_location", str(root_dir / "alembic"))

    prev_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url

    try:
        yield {"config": config, "db_url": db_url, "db_path": db_path}
    finally:
        if prev_url:
            os.environ["DATABASE_URL"] = prev_url
        else:
            os.environ.pop("DATABASE_URL", None)
        try:
            if db_path.exists():
                db_path.unlink(missing_ok=True)
            Path(temp_dir).rmdir()
        except OSError:
            pass


def test_alembic_migration_upgrade_and_downgrade_lifecycle(temp_alembic_db):
    """Verifica el ciclo de vida completo de migración: upgrade head -> verificar tablas -> downgrade base."""
    config = temp_alembic_db["config"]
    db_url = temp_alembic_db["db_url"]

    # 1. Aplicar migración inicial
    command.upgrade(config, "head")

    # 2. Inspeccionar esquema relacional resultante con NullPool para no retener el archivo
    engine = create_engine(db_url, poolclass=pool.NullPool)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "invoices" in tables
    assert "alembic_version" in tables

    # Validar columnas críticas de la tabla invoices
    columns = {col["name"]: col for col in inspector.get_columns("invoices")}
    assert "id" in columns
    assert "numero_factura" in columns
    assert "fecha_emision" in columns
    assert "nombre_proveedor" in columns
    assert "total" in columns
    assert "impuestos" in columns
    assert "moneda" in columns
    assert "estado" in columns
    assert "created_at" in columns

    # Validar índices creados
    indices = [idx["name"] for idx in inspector.get_indexes("invoices")]
    assert "ix_invoices_numero_factura" in indices
    assert "ix_invoices_estado" in indices

    engine.dispose()

    # 3. Revertir migración a base
    command.downgrade(config, "base")

    # 4. Verificar que la tabla invoices ya no existe
    engine_after = create_engine(db_url, poolclass=pool.NullPool)
    inspector_after = inspect(engine_after)
    remaining_tables = inspector_after.get_table_names()
    assert "invoices" not in remaining_tables

    engine_after.dispose()
