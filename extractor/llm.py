"""
Módulo de fallback con LLM estructurado (OpenAI) para InvoiceToSheet.
Se activa cuando los extractores basados en reglas producen advertencias.
"""

import logging
import os

from schemas import InvoiceData

logger = logging.getLogger("InvoiceExtractor.LLM")

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None  # type: ignore
    OPENAI_AVAILABLE = False


def is_valid_openai_api_key(api_key: str | None) -> bool:
    """Valida que la clave de API de OpenAI sea válida y no sea un marcador de posición."""
    if not api_key or not isinstance(api_key, str):
        return False
    cleaned = api_key.strip()
    if not cleaned or len(cleaned) < 5:
        return False
    placeholders = {
        "your_openai_api_key_here",
        "your_api_key_here",
        "your-api-key",
        "replace_me",
        "none",
        "null",
        "undefined",
    }
    return cleaned.lower() not in placeholders


def extract_with_llm(raw_text: str, filename: str) -> InvoiceData | None:
    """
    Fallback usando OpenAI con structured outputs para documentos complejos o desordenados.
    Se activa únicamente si OPENAI_API_KEY está configurada en el entorno con una clave válida.
    """
    raw_api_key = os.getenv("OPENAI_API_KEY")
    if not is_valid_openai_api_key(raw_api_key) or not OPENAI_AVAILABLE:
        return None

    api_key = raw_api_key.strip() if raw_api_key else ""
    try:
        client = OpenAI(api_key=api_key)
        prompt = (
            "Eres un asistente contable de precisión. Extrae los datos clave de la siguiente factura "
            "y responde estrictamente conforme al esquema especificado."
        )

        response = client.beta.chat.completions.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Archivo: {filename}\n\nTexto de la factura:\n{raw_text[:4000]}",
                },
            ],
            response_format=InvoiceData,
            temperature=0.0,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            return None
        parsed.nombre_archivo_origen = filename
        parsed.metodo_extraccion = "llm"
        return parsed
    except Exception as e:
        err_msg = str(e)
        if api_key and api_key in err_msg:
            err_msg = err_msg.replace(api_key, "[REDACTED_API_KEY]")
        logger.error(f"Error en fallback LLM: {err_msg}")
        return None
