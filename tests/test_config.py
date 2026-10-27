"""
Pruebas unitarias para el módulo central de configuración tipada config.py.
Valida carga por defecto, variables personalizadas y excepciones de configuración.
"""

import os

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


def test_read_secret_from_file_suffix_convention(tmp_path, monkeypatch):
    """Verifica que read_secret resuelva secretos montados mediante la convención _FILE."""
    from config import read_secret

    secret_file = tmp_path / "secret_openai_key.txt"
    secret_file.write_text("sk-file-provisioned-secret-key-123456", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resolved = read_secret("OPENAI_API_KEY")
    assert resolved == "sk-file-provisioned-secret-key-123456"

    # Settings.load() debe incorporar el secreto del archivo automáticamente
    s = Settings.load()
    assert s.openai_api_key == "sk-file-provisioned-secret-key-123456"


def test_read_secret_fallback_to_default_and_env(monkeypatch):
    """Verifica fallback transparente a variable de entorno y valor por defecto."""
    from config import read_secret

    monkeypatch.delenv("CUSTOM_SECRET_FILE", raising=False)
    monkeypatch.delenv("CUSTOM_SECRET", raising=False)

    assert read_secret("CUSTOM_SECRET", default="fallback-val") == "fallback-val"

    monkeypatch.setenv("CUSTOM_SECRET", "env-direct-value")
    assert read_secret("CUSTOM_SECRET", default="fallback-val") == "env-direct-value"


def test_read_secret_from_k8s_secrets_path(monkeypatch):
    """Verifica que read_secret resuelva secretos montados en /run/secrets/ en entornos Kubernetes/Docker."""
    from unittest.mock import mock_open, patch

    from config import read_secret

    monkeypatch.delenv("DATABASE_URL_FILE", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    fake_secret = "postgresql://prod_k8s_user:k8s_secure_pass@db:5432/invoices"
    expected_path = os.path.join("/run/secrets", "database_url")

    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: os.path.normpath(p) == os.path.normpath(expected_path),
        ),
        patch("builtins.open", mock_open(read_data=fake_secret)),
    ):
        resolved = read_secret("DATABASE_URL")
        assert resolved == fake_secret
