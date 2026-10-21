"""
Módulo de configuración centralizada y validación estricta para InvoiceToSheet.
Proporciona tipado Pydantic v2 para variables de entorno y soporte para inyección de secretos.
"""

import os

from pydantic import BaseModel, Field, field_validator


class ConfigurationError(ValueError):
    """Se lanza cuando una variable de configuración crítica contiene valores malformados o no válidos."""

    pass


def read_secret(var_name: str, default: str = "") -> str:
    """
    Resuelve el valor de un secreto priorizando fuentes seguras y managers de secretos
    (Docker secrets, Kubernetes secrets montados en /run/secrets/ o sufijo _FILE)
    antes de recurrir a variables de entorno en texto plano.
    """
    # 1. Convención estándar _FILE (ej. OPENAI_API_KEY_FILE=/secrets/openai_key)
    file_var = f"{var_name}_FILE"
    file_path = os.getenv(file_var)
    if file_path and os.path.isfile(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass

    # 2. Convención Docker / Kubernetes secrets (/run/secrets/<secret_name>)
    k8s_secret_path = os.path.join("/run/secrets", var_name.lower())
    if os.path.isfile(k8s_secret_path):
        try:
            with open(k8s_secret_path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass

    # 3. Fallback a variable de entorno estándar
    return os.getenv(var_name, default)


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
        """Carga la configuración desde gestores de secretos o variables de entorno activas."""
        try:
            return cls(
                database_url=read_secret("DATABASE_URL", "sqlite:///./invoices.db"),
                openai_api_key=read_secret("OPENAI_API_KEY", ""),
                sentry_dsn=read_secret("SENTRY_DSN", ""),
                app_env=read_secret("APP_ENV", "production"),
                allowed_origins=os.getenv("ALLOWED_ORIGINS", "*"),
                tesseract_path=os.getenv("TESSERACT_PATH", ""),
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Error de validación en configuración: {e}") from e


settings = Settings.load()
