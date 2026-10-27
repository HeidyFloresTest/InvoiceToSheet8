"""
Servidor Principal FastAPI para InvoiceToSheet.
Orquesta los endpoints de extracción de facturas PDF, exportación a Excel,
telemetría y entrega de la interfaz gráfica estática.
"""

import os

import sentry_sdk
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import InvoiceRepository, get_db, init_db
from excel_generator import generate_invoice_excel
from extractor import (
    InvalidInvoiceFormatError,
    InvoiceExtractionError,
    PayloadTooLargeError,
    extract_invoice_from_pdf,
)
from observability import (
    ErrorDetail,
    ObservabilityAndSecurityMiddleware,
    metrics,
    setup_logger,
)
from schemas import (
    BatchExtractResponse,
    ExportExcelRequest,
    InvoiceData,
    InvoiceHistoryItem,
    InvoiceHistoryResponse,
    PaginatedInvoicesResponse,
)

logger = setup_logger("InvoiceToSheetServer")


def init_sentry() -> bool:
    """Inicializa Sentry SDK condicionalmente si SENTRY_DSN está presente en el entorno."""
    dsn = os.getenv("SENTRY_DSN")
    if dsn and dsn.strip():
        sentry_sdk.init(
            dsn=dsn.strip(),
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        return True
    return False


# Inicialización condicional de Sentry para error tracking en producción
init_sentry()


# Límite máximo de tamaño por archivo: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Instanciación de la aplicación FastAPI
app = FastAPI(
    title="InvoiceToSheet API",
    description="Microservicio de extracción contable inteligente y consolidación en Excel.",
    version="1.3.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware de Seguridad y Observabilidad
app.add_middleware(ObservabilityAndSecurityMiddleware)

# Configuración de CORS segura (restringida a orígenes confiables por defecto)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(InvoiceExtractionError)
async def invoice_extraction_error_handler(request: Request, exc: InvoiceExtractionError):
    """Mapea excepciones tipadas de dominio a respuestas JSON estructuradas con ErrorDetail."""
    request_id = getattr(request.state, "request_id", None)
    error_detail = ErrorDetail(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details or None,
    )
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code == "PAYLOAD_TOO_LARGE":
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif exc.code in ("OCR_UNAVAILABLE", "LLM_FALLBACK_ERROR"):
        status_code = status.HTTP_502_BAD_GATEWAY
    return JSONResponse(status_code=status_code, content=error_detail.model_dump())


# Rutas de archivos estáticos
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)


# =====================================================================
# ENDPOINTS DE SALUD Y TELEMETRÍA (OBSERVABILIDAD)
# =====================================================================


@app.get("/health", tags=["Observabilidad"], summary="Verificación de salud del microservicio")
async def health_check():
    """Retorna el estado de disponibilidad del microservicio y métricas básicas de uptime."""
    snapshot = metrics.get_snapshot()
    return {
        "status": "healthy",
        "service": "InvoiceToSheet API",
        "version": app.version,
        "uptime_seconds": snapshot["uptime_seconds"],
    }


@app.get("/api/metrics", tags=["Observabilidad"], summary="Métricas de rendimiento y uso (JSON)")
async def get_metrics():
    """Retorna estadísticas operativas en tiempo real en formato JSON estructurado."""
    return metrics.get_snapshot()


@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["Observabilidad"],
    summary="Métricas estándar de Prometheus (OpenMetrics)",
)
async def get_prometheus_metrics():
    """Exporta métricas del microservicio en formato de texto plano compatible con Prometheus / Grafana."""
    return PlainTextResponse(
        content=metrics.to_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# =====================================================================
# ENDPOINTS DE EXTRACCIÓN Y EXPORTACIÓN
# =====================================================================


# Inicialización del esquema de base de datos relacional
init_db()


@app.post(
    "/api/extract",
    response_model=BatchExtractResponse,
    status_code=status.HTTP_200_OK,
    tags=["Extracción"],
    summary="Extrae datos estructurados de uno o múltiples archivos PDF en lote",
)
async def extract_invoices(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Recibe un conjunto de archivos PDF mediante multipart/form-data.
    Procesa cada archivo de forma aislada en memoria:
    - Valida tamaño máximo permitido (25MB por archivo).
    - Si un archivo falla o está dañado, no interrumpe el procesamiento del resto.
    - Persiste el histórico de facturas en base de datos relacional (ORM SQLite).
    - Devuelve la lista consolidada de resultados con estadísticas globales.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No se enviaron archivos para procesar."
        )

    results: list[InvoiceData] = []
    exitosos = 0
    advertencias = 0
    errores = 0

    for file in files:
        filename = file.filename or "archivo_sin_nombre.pdf"

        # Validación de formato por extensión
        if not filename.lower().endswith(".pdf"):
            format_err = InvalidInvoiceFormatError(
                f"Formato no soportado para '{filename}'. Debe ser un archivo .pdf."
            )
            results.append(
                InvoiceData(
                    nombre_archivo_origen=filename,
                    estado="error",
                    mensaje_error=format_err.message,
                )
            )
            errores += 1
            continue

        try:
            content = await file.read()

            # Validación de tamaño de archivo
            if len(content) > MAX_FILE_SIZE_BYTES:
                size_err = PayloadTooLargeError(
                    f"El archivo '{filename}' excede el tamaño máximo permitido de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
                )
                results.append(
                    InvoiceData(
                        nombre_archivo_origen=filename,
                        estado="error",
                        mensaje_error=size_err.message,
                    )
                )
                errores += 1
                continue

            # Extracción aislada
            invoice = extract_invoice_from_pdf(content, filename)
            results.append(invoice)

            if invoice.estado == "success":
                exitosos += 1
            elif invoice.estado == "warning":
                advertencias += 1
            else:
                errores += 1

        except InvoiceExtractionError as e:
            logger.warning(
                f"Error de dominio de extracción en '{filename}': [{e.code}] {e.message}"
            )
            results.append(
                InvoiceData(
                    nombre_archivo_origen=filename,
                    estado="error",
                    mensaje_error=e.message,
                )
            )
            errores += 1
        except Exception as e:
            logger.error(f"Fallo no controlado procesando '{filename}': {str(e)}", exc_info=True)
            results.append(
                InvoiceData(
                    nombre_archivo_origen=filename,
                    estado="error",
                    mensaje_error=f"Error inesperado al leer el documento: {str(e)}",
                )
            )
            errores += 1

    # Registrar telemetría
    metrics.record_invoices(success=exitosos, warning=advertencias, error=errores)

    # Persistencia relacional en base de datos mediante capa ORM
    try:
        repo = InvoiceRepository(db)
        repo.save_batch(results)
    except Exception as e:
        logger.error(f"Error al persistir lote en base de datos: {e}")

    return BatchExtractResponse(
        total_archivos=len(files),
        total_exitosos=exitosos,
        total_con_advertencia=advertencias,
        total_con_error=errores,
        facturas=results,
    )


@app.get(
    "/api/invoices/history",
    response_model=InvoiceHistoryResponse,
    tags=["Historial"],
    summary="Obtiene el historial paginado de facturas procesadas",
)
async def get_invoice_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retorna las facturas registradas en la base de datos con paginación."""
    repo = InvoiceRepository(db)
    items = repo.list_invoices(skip=skip, limit=limit)
    total = repo.count_total()
    return InvoiceHistoryResponse(
        total=total,
        skip=skip,
        limit=limit,
        invoices=[InvoiceHistoryItem.model_validate(item) for item in items],
    )


@app.get(
    "/api/invoices",
    response_model=PaginatedInvoicesResponse,
    tags=["Historial"],
    summary="Listado paginado de facturas con navegación y filtrado por estado",
)
async def list_invoices_paginated(
    page: int = Query(1, ge=1, description="Número de página (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Cantidad de elementos por página"),
    status_filter: str | None = Query(
        None, alias="status", description="Filtro opcional por estado (success, warning, error)"
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna facturas con paginación formal (page, page_size, total_pages, total_items)
    y soporte para filtrado por estado de extracción contable.
    """
    repo = InvoiceRepository(db)
    skip = (page - 1) * page_size
    items = repo.list_invoices(skip=skip, limit=page_size, status=status_filter)
    total_items = repo.count_total(status=status_filter)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

    return PaginatedInvoicesResponse(
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items,
        status_filter=status_filter,
        invoices=[InvoiceHistoryItem.model_validate(item) for item in items],
    )


@app.get(
    "/api/invoices/{invoice_id}",
    response_model=InvoiceHistoryItem,
    tags=["Historial"],
    summary="Obtiene el detalle de una factura específica del historial",
)
async def get_invoice_by_id(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """Busca y retorna una factura específica por su ID primario."""
    repo = InvoiceRepository(db)
    item = repo.get_by_id(invoice_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura con ID {invoice_id} no encontrada.",
        )
    return InvoiceHistoryItem.model_validate(item)


@app.post(
    "/api/export-excel",
    tags=["Exportación"],
    summary="Genera y descarga directamente un archivo Excel consolidado en memoria",
)
async def export_to_excel(payload: ExportExcelRequest):
    """
    Recibe la lista de facturas (pueden haber sido editadas o corregidas en el frontend).
    Genera el archivo .xlsx formateado profesionalmente y lo transmite de vuelta
    al navegador sin almacenamiento temporal en el disco del servidor.
    """
    if not payload.facturas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay facturas para generar el reporte de Excel.",
        )

    try:
        excel_stream = generate_invoice_excel(payload.facturas)
        metrics.record_excel()
        filename = "facturas_consolidadas.xlsx"

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }

        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except Exception as e:
        logger.error(f"Error generando archivo Excel: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar la hoja de cálculo: {str(e)}",
        ) from e


# =====================================================================
# SERVIDORES DE ARCHIVOS ESTÁTICOS Y ENTRADA DE FRONTEND
# =====================================================================

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["Frontend"])
async def serve_index():
    """Entrega la interfaz gráfica web en un solo archivo."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "InvoiceToSheet API lista."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
