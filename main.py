"""
Servidor Principal FastAPI para InvoiceToSheet.
Orquesta los endpoints de extracción de facturas PDF, exportación a Excel y
la entrega de la interfaz gráfica estática.
"""

import os
import logging
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from schemas import InvoiceData, BatchExtractResponse, ExportExcelRequest
from extractor import extract_invoice_from_pdf
from excel_generator import generate_invoice_excel

logger = logging.getLogger("InvoiceToSheetServer")
logging.basicConfig(level=logging.INFO)

# Instanciación de la aplicación FastAPI
app = FastAPI(
    title="InvoiceToSheet API",
    description="Microservicio de extracción contable inteligente y consolidación en Excel.",
    version="1.0.0"
)

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
# ENDPOINTS DE LA API
# =====================================================================

@app.get("/health", tags=["Salud"])
async def health_check():
    """Verifica que el servicio esté activo y listo para procesar solicitudes."""
    return {"status": "ok", "service": "InvoiceToSheet API"}


@app.post(
    "/api/extract",
    response_model=BatchExtractResponse,
    status_code=status.HTTP_200_OK,
    tags=["Extracción"],
    summary="Extrae datos estructurados de uno o múltiples archivos PDF en lote"
)
async def extract_invoices(files: List[UploadFile] = File(...)):
    """
    Recibe un conjunto de archivos PDF mediante multipart/form-data.
    Procesa cada archivo de forma aislada en memoria:
    - Si un archivo falla o está dañado, no interrumpe el procesamiento del resto.
    - Devuelve la lista consolidada de resultados con estadísticas globales.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron archivos para procesar."
        )

    results: List[InvoiceData] = []
    exitosos = 0
    advertencias = 0
    errores = 0

    for file in files:
        filename = file.filename or "archivo_sin_nombre.pdf"
        
        # Validación de extensión
        if not filename.lower().endswith(".pdf"):
            results.append(InvoiceData(
                nombre_archivo_origen=filename,
                estado="error",
                mensaje_error="Formato no soportado. Debe ser un archivo .pdf."
            ))
            errores += 1
            continue

        try:
            # Lectura en memoria segura
            content = await file.read()
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
            results.append(InvoiceData(
                nombre_archivo_origen=filename,
                estado="error",
                mensaje_error=f"Error inesperado al leer el documento: {str(e)}"
            ))
            errores += 1

    return BatchExtractResponse(
        total_archivos=len(files),
        total_exitosos=exitosos,
        total_con_advertencia=advertencias,
        total_con_error=errores,
        facturas=results
    )


@app.post(
    "/api/export-excel",
    tags=["Exportación"],
    summary="Genera y descarga directamente un archivo Excel consolidado en memoria"
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
            detail="No hay facturas para generar el reporte de Excel."
        )

    try:
        excel_stream = generate_invoice_excel(payload.facturas)
        filename = "facturas_consolidadas.xlsx"
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }

        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error generando archivo Excel: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar la hoja de cálculo: {str(e)}"
        )


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
    return {"message": "InvoiceToSheet API lista. Coloca index.html en /static para la interfaz."}


if __name__ == "__main__":
    import uvicorn
    # Arranque local para pruebas
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
