"""
Servidor Principal FastAPI para InvoiceToSheet.
Orquesta los endpoints de extracción de facturas PDF, exportación a Excel,
telemetría y entrega de la interfaz gráfica estática.
"""

import os

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from excel_generator import generate_invoice_excel
from extractor import extract_invoice_from_pdf
from observability import ObservabilityAndSecurityMiddleware, metrics, setup_logger
from schemas import BatchExtractResponse, ExportExcelRequest, InvoiceData

logger = setup_logger("InvoiceToSheetServer")

# Límite máximo de tamaño por archivo: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Instanciación de la aplicación FastAPI
app = FastAPI(
    title="InvoiceToSheet API",
    description="Microservicio de extracción contable inteligente y consolidación en Excel.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware de Seguridad y Observabilidad
app.add_middleware(ObservabilityAndSecurityMiddleware)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "version": "1.0.0",
        "uptime_seconds": snapshot["uptime_seconds"],
    }


@app.get("/api/metrics", tags=["Observabilidad"], summary="Métricas de rendimiento y uso")
async def get_metrics():
    """Retorna estadísticas operativas en tiempo real (invoices procesadas, tasas de éxito, llamadas)."""
    return metrics.get_snapshot()


# =====================================================================
# ENDPOINTS DE EXTRACCIÓN Y EXPORTACIÓN
# =====================================================================


@app.post(
    "/api/extract",
    response_model=BatchExtractResponse,
    status_code=status.HTTP_200_OK,
    tags=["Extracción"],
    summary="Extrae datos estructurados de uno o múltiples archivos PDF en lote",
)
async def extract_invoices(files: list[UploadFile] = File(...)):
    """
    Recibe un conjunto de archivos PDF mediante multipart/form-data.
    Procesa cada archivo de forma aislada en memoria:
    - Valida tamaño máximo permitido (25MB por archivo).
    - Si un archivo falla o está dañado, no interrumpe el procesamiento del resto.
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
            results.append(
                InvoiceData(
                    nombre_archivo_origen=filename,
                    estado="error",
                    mensaje_error="Formato no soportado. Debe ser un archivo .pdf.",
                )
            )
            errores += 1
            continue

        try:
            content = await file.read()

            # Validación de tamaño de archivo
            if len(content) > MAX_FILE_SIZE_BYTES:
                results.append(
                    InvoiceData(
                        nombre_archivo_origen=filename,
                        estado="error",
                        mensaje_error=f"El archivo excede el tamaño máximo permitido de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
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

    return BatchExtractResponse(
        total_archivos=len(files),
        total_exitosos=exitosos,
        total_con_advertencia=advertencias,
        total_con_error=errores,
        facturas=results,
    )


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
