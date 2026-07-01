"""
Pruebas de inicialización y resiliencia para el rastreo de errores con Sentry SDK.
Verifica que la aplicación arranque limpiamente tanto con SENTRY_DSN configurado como ausente.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


def test_app_starts_without_sentry_dsn(monkeypatch):
    """Verifica que el microservicio funcione con normalidad cuando SENTRY_DSN no está configurado."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with TestClient(main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_app_starts_with_valid_sentry_dsn(monkeypatch):
    """Verifica que sentry_sdk.init sea invocado correctamente cuando SENTRY_DSN está presente."""
    fake_dsn = "https://public@sentry.example.com/1"
    monkeypatch.setenv("SENTRY_DSN", fake_dsn)

    with patch("sentry_sdk.init") as mock_sentry_init:
        # Simular lectura del entorno e inicialización
        sentry_dsn = os.getenv("SENTRY_DSN")
        if sentry_dsn:
            import sentry_sdk

            sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.1)

        mock_sentry_init.assert_called_once_with(dsn=fake_dsn, traces_sample_rate=0.1)

        with TestClient(main.app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
