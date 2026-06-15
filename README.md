# InvoiceToSheet 📄 ➔ 📊

**InvoiceToSheet** es un MVP web modular, robusto y de alto rendimiento diseñado para la extracción automática de datos contables desde facturas en formato PDF (digitales o escaneadas) y su consolidación directa en archivos Excel (`.xlsx`) estilizados y listos para contabilidad.

---

## 🏗 Arquitectura del Sistema

El sistema implementa un modelo de procesamiento desacoplado y seguro en memoria, evitando almacenar comprobantes sensibles en el disco del servidor.

```
+-------------------------------------------------------------+
|                     Frontend Web                            |
|  (HTML5 + Tailwind CSS CDN + JS Vanilla + Drag & Drop)      |
+------------------------------+------------------------------+
                               |
                   1. Enviar lote de PDFs
                      (POST /api/extract)
                               v
+-------------------------------------------------------------+
|                      FastAPI Backend                        |
|                                                             |
|   +-----------------------------------------------------+   |
|   |         Pipeline Híbrido de Extracción              |   |
|   |                                                     |   |
|   |  1. Lectura en Memoria (pdfplumber)                 |   |
|   |  2. Fallback OCR (pytesseract + pdf2image)          |   |
|   |  3. Motor Heurístico Regex de Alta Tolerancia       |   |
|   |  4. Fallback LLM Opcional (OpenAI Structured Data)  |   |
|   +--------------------------+--------------------------+   |
|                              v                              |
|               2. Retorno JSON (InvoiceData[])               |
+------------------------------+------------------------------+
                               v
+-------------------------------------------------------------+
|              Tabla Interactiva de Previsualización          |
|  - Edición en línea de celdas erróneas o no identificadas   |
|  - Recálculo en tiempo real de métricas contables (KPIs)    |
+------------------------------+------------------------------+
                               |
                 3. Exportar datos editados
                   (POST /api/export-excel)
                               v
+-------------------------------------------------------------+
|              Generador de Excel (openpyxl)                  |
|  - Tipos de datos numéricos y fechas reales                 |
|  - Cabeceras corporativas y estilo contable                 |
|  - Fórmulas dinámicas SUM en pie de página                  |
|  - Descarga directa en memoria (BytesIO Streaming)          |
+-------------------------------------------------------------+
```

---

## 📁 Estructura del Proyecto

```plaintext
Pruebas/
├── .env.example            # Plantilla de variables de entorno (OpenAI, Tesseract)
├── requirements.txt        # Dependencias fijadas del proyecto
├── schemas.py              # Esquemas de datos Pydantic (InvoiceData, Lotes)
├── extractor.py            # Motor de extracción híbrido (pdfplumber + OCR + Regex + LLM)
├── excel_generator.py      # Creación y formateo profesional de hojas .xlsx
├── main.py                 # Aplicación FastAPI y endpoints RESTful
├── test_pipeline.py        # Suite de pruebas unitarias
└── static/
    └── index.html          # Interfaz de usuario moderna en un solo archivo
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Prerrequisitos
- Python 3.10 o superior instalado.

### 2. Crear un entorno virtual (Recomendado)

En Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En Linux/macOS (Bash):
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (Opcional)
Si deseas habilitar el fallback con inteligencia artificial para facturas con formatos desestructurados:
```bash
cp .env.example .env
```
Edita `.env` e introduce tu clave:
```ini
OPENAI_API_KEY=tu_clave_de_openai_aqui
```

### 5. Iniciar el Servidor de Desarrollo
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Abre tu navegador en:
👉 **`http://127.0.0.1:8000`**

Documentación interactiva de la API:
👉 **`http://127.0.0.1:8000/docs`**

---

## 🔍 Pipeline de Extracción y Resiliencia

1. **Aislamiento por Archivo:** El endpoint `/api/extract` itera de forma protegida sobre cada `UploadFile`. Si un PDF está corrupto o protegido con contraseña, registra el estado `error` para esa fila sin interrumpir el procesamiento del resto del lote.
2. **Normalización Numérica Tolerante:** Reconoce formatos internacionales como `1,234.50` y formatos hispanoamericanos/europeos `1.234,50`, eliminando símbolos de moneda y espacios de forma segura.
3. **Normalización de Fechas:** Convierte tanto formatos numéricos (`DD/MM/YYYY`, `YYYY-MM-DD`) como fechas en lenguaje natural (`15 de enero de 2024`) al formato estándar ISO `YYYY-MM-DD`.
4. **Reconciliación Matemática:** Verifica si `Subtotal + Impuestos == Total`. Si uno de los tres campos no fue detectado en el texto pero los otros dos sí, calcula el faltante automáticamente.
5. **Generación 100% en Memoria:** Ni los PDFs ni los archivos Excel se guardan en el disco duro del servidor, garantizando cumplimiento de normativas de privacidad de datos (GDPR / datos contables confidenciales).

---

## 🧪 Ejecución de Pruebas Unitarias

Para validar el extractor y la generación de Excel:
```bash
python -m unittest test_pipeline.py
```
