"""
Pruebas unitarias para el módulo central de configuración tipada config.py.
Valida carga por defecto, variables personalizadas y excepciones de configuración.
"""

import pytest

from config import ConfigurationError, Settings


def test_settings_load_defaults():
    """Verifica que las configuraciones por defecto sean seguras y operacionales."""
    s = Settings()
    assert s.database_url == "sqlite:///./invoices.db"
    assert s.openai_api_key == ""
    assert s.sentry_dsn == ""
    assert s.app_env == "production"


def test_settings_load_from_environment(monkeypatch):
    """Verifica que Settings.load() lea las variables del entorno correctamente."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/invoices")
    monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.io/123456")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-valid-length-test-key-123456789")

    s = Settings.load()
    assert s.database_url == "postgresql://user:pass@localhost:5432/invoices"
    assert s.sentry_dsn == "https://key@sentry.io/123456"
    assert s.openai_api_key == "sk-valid-length-test-key-123456789"


def test_settings_malformed_openai_key_raises_configuration_error(monkeypatch):
    """Verifica que una clave de OpenAI incompleta o malformada lance ConfigurationError."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-short")

    with pytest.raises(ConfigurationError) as exc_info:
        Settings.load()

    assert "OPENAI_API_KEY malformada" in str(exc_info.value)
