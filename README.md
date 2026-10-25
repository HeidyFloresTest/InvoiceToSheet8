# InvoiceToSheet 📄 ➔ 📊

[![CI Pipeline](https://github.com/HeidyFloresTest/InvoiceToSheet9/actions/workflows/ci.yml/badge.svg)](https://github.com/HeidyFloresTest/InvoiceToSheet9/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Coverage: 94%](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/HeidyFloresTest/InvoiceToSheet9)
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
- [Observabilidad y Arquitectura](#-observabilidad-y-arquitectura)
- [Seguridad](#-seguridad)
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
# Construir e iniciar el contenedor en segundo plano
docker compose up -d --build
```

Verificación inmediata del despliegue y estado de salud:
```bash
$ curl -s http://localhost:8000/health
{"status":"healthy","service":"InvoiceToSheet API","version":"1.4.0","database":"connected","ocr_engine":"available","uptime_seconds":1.20}
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
git clone https://github.com/HeidyFloresTest/InvoiceToSheet9.git
cd InvoiceToSheet9
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

### 3. Instalar dependencias con bloqueo estricto (Reproducibilidad Garantizada)
El repositorio incluye los lockfiles oficiales (`uv.lock` y `poetry.lock`) como fuentes de verdad para garantizar instalaciones 100% reproducibles y deterministas desde un clon limpio:

Con `uv` (Recomendado, ultra-rápido):
```bash
uv sync
```

Con `poetry`:
```bash
poetry install
```

O con `pip` tradicional:
```bash
pip install -r requirements-dev.txt
```

### 4. Configurar variables de entorno (Opcional)
```bash
cp .env.example .env
```
Edita `.env` para agregar tu clave de OpenAI, configuración de base de datos o Sentry si aplica.

### 5. Iniciar el servidor local
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Ejecución de Pruebas y Cobertura

El proyecto cuenta con una suite completa y 100% hermética de **108 pruebas unitarias, de integración simulada y de seguridad** que cubren validación de esquemas, motor de expresiones regulares, normalizadores internacionales de divisas (USD, EUR, MXN, CLP, COP, PEN, BRL, GBP, CHF, JPY, CAD, AUD), preprocesamiento OCR adaptativo, paginación con filtros en base de datos, mitigaciones OWASP, resolución de secretos y endpoints HTTP:

```bash
# Ejecutar suite hermética completa (excluye dependencias externas de binarios del sistema)
pytest --cov=. --cov-report=term-missing
```

Salida verificable de la ejecución (`92.9%` de cobertura real en entorno limpio):
```text
=============================== tests coverage ================================
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
alembic/env.py                31      8    74%   38-47, 71-73, 77
config.py                     43      2    95%   30, 83
database.py                   62      0   100%
excel_generator.py            90      0   100%
extractor/__init__.py          7      0   100%
extractor/engine.py           93      9    90%   95, 97, 136-140, 183, 185
extractor/exceptions.py       23      0   100%
extractor/llm.py              39      4    90%   17-19, 72
extractor/normalizers.py      51      2    96%   58-59
extractor/ocr.py              40      8    80%   19-24, 49-50
extractor/pipeline.py         40      0   100%
main.py                      163     24    85%   148, 170-171, 179-180, 265, 327
observability.py             132      2    98%   214, 266
schemas.py                    56      0   100%
--------------------------------------------------------
TOTAL                        891     63    93%
Coverage XML written to file coverage.xml
Required test coverage of 80.0% reached. Total coverage: 92.93%
===================== 108 passed, 1 deselected in 11.53s ======================
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
| `GET` | `/health` | Verificación de disponibilidad y preparación (*readiness probe*): conectividad con base de datos, motor OCR y uptime. |
| `GET` | `/healthz` | Liveness y readiness probe compatible con orquestadores Kubernetes y load balancers. |
| `GET` | `/api/health` | Alias RESTful para verificación de salud y dependencias del sistema. |
| `GET` | `/metrics` | Telemetría estándar de Prometheus / OpenMetrics para scraping. |
| `GET` | `/api/metrics` | Telemetría en tiempo real en formato JSON estructurado. |
| `GET` | `/api/errors/summary` | Resumen de telemetría de errores estructurados en memoria categorizados por código y tipo. |
| `GET` | `/api/errors/recent` | Consulta en buffer circular de errores recientes con IDs de correlación y detalles. |
| `POST` | `/api/extract` | Procesamiento por lotes de comprobantes PDF (`multipart/form-data`). |
| `POST` | `/api/export-excel` | Generación en memoria y descarga del archivo `.xlsx` consolidado. |
| `GET` | `/api/invoices` | Listado paginado formal (page, page_size, total_pages) con filtrado opcional por estado. |
| `GET` | `/api/invoices/history` | Consulta paginada del historial de facturas persistidas en la base de datos ORM. |
| `GET` | `/api/invoices/{id}` | Búsqueda y auditoría de factura individual por ID primario. |
| `GET` | `/docs` | Documentación interactiva Swagger / OpenAPI. |

---

## 🛡 Observabilidad y Arquitectura

- **Arquitectura de Software:** Consulta el diseño detallado del pipeline, flujo de datos y diagramas de componentes en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Código de Conducta:** Consulta nuestro compromiso comunitario en [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Rastreo de Errores Estructurados en Memoria:** `StructuredErrorTracker` mantiene un buffer circular thread-safe con auditoría de incidencias categorizadas por tipo y código sin dependencia forzada de servicios externos (`GET /api/errors/summary` y `GET /api/errors/recent`).
- **Monitoreo de Excepciones en Producción (Sentry):** Integración nativa con `sentry-sdk[fastapi]`. Configura la variable `SENTRY_DSN` en tu entorno o `.env` para captura automática de trazas de error en tiempo real (si no está definida, opera como *no-op* sin interrumpir el servicio).
- **Migraciones de Base de Datos (Alembic):** Control de versiones transaccional del esquema de base de datos relacional. Ejecuta `alembic upgrade head` para sincronizar cambios de forma determinista y sin riesgo de deriva de esquema (*schema drift*).
- **Trazabilidad:** Cada petición genera un identificador único `X-Request-ID` que se propaga a los logs estructurados JSON para auditoría.
- **Resiliencia ante Fallos:** Si un archivo dentro de un lote está dañado o protegido con contraseña, el sistema aísla el error y procesa el resto sin interrupciones.
- **Protección de Datos:** Ningún comprobante ni archivo Excel se almacena en el disco duro del servidor; todo el procesamiento ocurre estrictamente en memoria (`io.BytesIO`).

---

## 🔒 Seguridad

Para consultar las políticas de seguridad de **InvoiceToSheet**, el modelo de amenazas STRIDE, el protocolo de reporte de vulnerabilidades y las directrices de aprovisionamiento y rotación de secretos en entornos productivos mediante Secret Managers (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager o Docker Secrets), consulta el documento formal [SECURITY.md](SECURITY.md).

- **Gestión Segura de Secretos en Producción:** Las credenciales (`DATABASE_URL`, `OPENAI_API_KEY`, `SENTRY_DSN`) se inyectan estrictamente vía Secret Managers y son validadas en el arranque por `config.Settings`, levantando `ConfigurationError` ante tokens truncados o malformados.
- **Cabeceras HTTP OWASP:** Inyección obligatoria de `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block` y `Referrer-Policy: strict-origin-when-cross-origin`.
- **Auditoría Continua de Dependencias:** Escaneo automatizado de vulnerabilidades en CI con `pip-audit` y Dependabot activo.

---

## 🔒 Reglas de Protección de Rama (`main`)

El pipeline de CI en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) define las verificaciones requeridas obligatorias (*required status checks*) para la rama `main`:
1. `Code Quality (Ruff Linter & Formatter)` (`lint`)
2. `Static Type Analysis (Mypy)` (`typecheck`)
3. `Test on Python 3.12 (ubuntu-latest)` (`test`)
4. `Dependency Security Audit (pip-audit)` (`security-audit`)
5. `Deploy Packaging Verification` (`deploy`)

Para más detalles sobre el proceso de contribución y versiones, consulta [CONTRIBUTING.md](CONTRIBUTING.md) y [CHANGELOG.md](CHANGELOG.md).

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia [MIT](LICENSE).
