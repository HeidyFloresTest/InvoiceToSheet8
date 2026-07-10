# InvoiceToSheet 📄 ➔ 📊

[![CI Pipeline](https://github.com/HeidyFloresTest/InvoiceToSheet1/actions/workflows/ci.yml/badge.svg)](https://github.com/HeidyFloresTest/InvoiceToSheet1/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Coverage: 91%](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/HeidyFloresTest/InvoiceToSheet1)
[![Docker Ready](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**InvoiceToSheet** es un microservicio y aplicación web moderna de alta resiliencia diseñada para la extracción contable automatizada desde facturas y comprobantes en formato PDF (digitales o escaneados) y su consolidación directa en planillas Excel (`.xlsx`) profesionales con tipos de datos nativos, formato de moneda y fórmulas contables.

---

## 📑 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Inicio Rápido con Docker](#-inicio-rápido-con-docker-recomendado)
- [Instalación Local para Desarrollo](#-instalación-local-para-desarrollo)
- [Ejecución de Pruebas y Cobertura](#-ejecución-de-pruebas-y-cobertura)
- [Calidad de Código y Linting](#-calidad-de-código-y-linting)
- [Referencia de la API REST](#-referencia-de-la-api-rest)
- [Observabilidad y Seguridad](#-observabilidad-y-seguridad)
- [Licencia](#-licencia)

---

## ✨ Características Principales

- **Procesamiento Híbrido Resiliente:** 
  1. Extracción de texto digital en memoria con `pdfplumber`.
  2. Fallback automático a OCR (`pytesseract` + `pdf2image`) para PDFs escaneados o imágenes.
  3. Motor de reglas de alta tolerancia con Regex tolerante a formatos de España, México, Chile, Colombia, Perú y estándares internacionales.
  4. Fallback opcional a LLM (OpenAI Structured Outputs) para formatos atípicos o no estructurados.
- **Generación Excel Profesional:** Archivos `.xlsx` creados 100% en memoria (`io.BytesIO`) con estilos contables corporativos, auto-ancho dinámico, tipos numéricos reales y fórmulas `=SUM(...)`.
- **Frontend Interactivo en un Solo Archivo:** Drag & Drop para lotes de 1 a 50+ archivos, barra de progreso, tarjetas KPI en tiempo real y tabla interactiva con edición en vivo antes de la descarga.
- **Observabilidad de Nivel Producción:** Logging estructurado en JSON, trazabilidad extremo a extremo con `X-Request-ID` y endpoint de telemetría `/api/metrics`.
- **Seguridad Rigurosa:** Cabeceras HTTP OWASP (`X-Content-Type-Options`, `X-Frame-Options`), validación de tamaño de archivo (máx. 25MB) y ejecución en contenedor con usuario sin privilegios.

---

## 🏗 Arquitectura del Sistema

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

## 🐳 Inicio Rápido con Docker (Recomendado)

La forma más rápida y reproducible de levantar el proyecto en un entorno sandbox aislado con todas las dependencias del sistema (Tesseract OCR, Poppler):

```bash
# Construir e iniciar el contenedor
docker compose up --build
```

Abre tu navegador en:
👉 **`http://localhost:8000`**

Para detener el servicio:
```bash
docker compose down
```

---

## 💻 Instalación Local para Desarrollo

### 1. Clonar el repositorio
```bash
git clone https://github.com/HeidyFloresTest/InvoiceToSheet.git
cd InvoiceToSheet
```

### 2. Crear y activar entorno virtual
En Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias de desarrollo y producción
```bash
pip install -r requirements-dev.txt
```

### 4. Configurar variables de entorno (Opcional)
```bash
cp .env.example .env
```
Edita `.env` para agregar tu clave de OpenAI o ruta personalizada a Tesseract si aplica.

### 5. Iniciar el servidor local
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Ejecución de Pruebas y Cobertura

El proyecto cuenta con una suite completa de **43 pruebas unitarias e integrales** que cubren validación de esquemas, normalizadores, motor regex, pipeline PDF, generador de Excel y endpoints HTTP.

Ejecutar pruebas con reporte de cobertura:
```bash
pytest
```

Para generar un reporte HTML interactivo de cobertura:
```bash
pytest --cov-report=html
# Abre htmlcov/index.html en tu navegador
```

---

## 🧹 Calidad de Código y Linting

El proyecto aplica estándares estrictos de estilo mediante [Ruff](https://github.com/astral-sh/ruff) y tipado estático con [Mypy](http://mypy-lang.org/):

```bash
# Análisis estático y verificación de reglas
ruff check .

# Formateo automático de código
ruff format .

# Verificación de tipos estáticos
mypy .
```

---

## 📡 Referencia de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Verificación de disponibilidad y tiempo activo del servicio. |
| `GET` | `/api/metrics` | Telemetría en vivo: facturas procesadas, tasas de éxito y tiempos. |
| `POST` | `/api/extract` | Procesamiento por lotes de comprobantes PDF (`multipart/form-data`). |
| `POST` | `/api/export-excel` | Generación en memoria y descarga del archivo `.xlsx` consolidado. |
| `GET` | `/docs` | Documentación interactiva Swagger / OpenAPI. |

---

## 🛡 Observabilidad y Seguridad

- **Monitoreo de Excepciones en Producción (Sentry):** Integración nativa con `sentry-sdk[fastapi]`. Configura la variable `SENTRY_DSN` en tu entorno o `.env` para captura automática de trazas de error en tiempo real (si no está definida, opera como *no-op* sin interrumpir el servicio).
- **Trazabilidad:** Cada petición genera un identificador único `X-Request-ID` que se propaga a los logs estructurados JSON para auditoría.
- **Resiliencia ante Fallos:** Si un archivo dentro de un lote está dañado o protegido con contraseña, el sistema aísla el error y procesa el resto sin interrupciones.
- **Protección de Datos:** Ningún comprobante ni archivo Excel se almacena en el disco duro del servidor; todo el procesamiento ocurre estrictamente en memoria (`io.BytesIO`).

---

## 🔒 Reglas de Protección de Rama (`main`)

El pipeline de CI en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) define las verificaciones requeridas obligatorias (*required status checks*) para la rama `main`:
1. `Code Quality (Ruff Linter & Formatter)` (`lint`)
2. `Static Type Analysis (Mypy)` (`typecheck`)
3. `Test on Python 3.12 (ubuntu-latest)` (`test`)
4. `Dependency Security Audit (pip-audit)` (`security-audit`)

Para más detalles sobre el proceso de contribución y versiones, consulta [CONTRIBUTING.md](CONTRIBUTING.md) y [CHANGELOG.md](CHANGELOG.md).

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia [MIT](LICENSE).
