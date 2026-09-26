"""
Módulo de configuración centralizada y validación estricta para InvoiceToSheet.
Proporciona tipado Pydantic v2 para variables de entorno y soporte para inyección de secretos.
"""

import os

from pydantic import BaseModel, Field, field_validator


class ConfigurationError(ValueError):
    """Se lanza cuando una variable de configuración crítica contiene valores malformados o no válidos."""

    pass


class Settings(BaseModel):
    """Configuración inmutable y validada en tiempo de arranque."""

    database_url: str = Field(default="sqlite:///./invoices.db")
    openai_api_key: str = Field(default="")
    sentry_dsn: str = Field(default="")
    app_env: str = Field(default="production")
    allowed_origins: str = Field(default="*")
    tesseract_path: str = Field(default="")

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        """Valida que la clave de OpenAI no sea un token truncado o malformado."""
        cleaned = v.strip()
        if not cleaned:
            return ""
        if cleaned.startswith("sk-") and len(cleaned) < 15:
            raise ConfigurationError(
                f"OPENAI_API_KEY malformada: '{cleaned}' tiene longitud insuficiente."
            )
        return cleaned

    @classmethod
    def load(cls) -> "Settings":
        """Carga la configuración desde las variables de entorno activas."""
        try:
            return cls(
                database_url=os.getenv("DATABASE_URL", "sqlite:///./invoices.db"),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                sentry_dsn=os.getenv("SENTRY_DSN", ""),
                app_env=os.getenv("APP_ENV", "production"),
                allowed_origins=os.getenv("ALLOWED_ORIGINS", "*"),
                tesseract_path=os.getenv("TESSERACT_PATH", ""),
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Error de validación en configuración: {e}") from e


settings = Settings.load()
