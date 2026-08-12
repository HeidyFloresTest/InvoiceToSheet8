# InvoiceToSheet Architecture & System Design

This document details the software architecture, data flow, pipeline lifecycle, and telemetry infrastructure of the **InvoiceToSheet** microservice.

---

## 1. High-Level Architecture Overview

InvoiceToSheet is designed as a stateless, horizontally-scalable FastAPI microservice specialized in extracting structured financial data from non-standard PDF invoices and consolidating them into enterprise Excel workbooks.

```mermaid
graph TD
    Client[Web Browser / API Client] -->|POST /api/extract| Middleware[Observability & Security Middleware]
    Middleware -->|Request ID & OWASP Headers| Router[FastAPI REST Controllers]
    
    subgraph Core Processing Pipeline
        Router -->|In-Memory Stream| Pipeline[Extractor Pipeline]
        Pipeline --> Plumber[pdfplumber Text Extraction]
        Plumber -->|Empty or Scanned PDF| OCR[Tesseract OCR Fallback]
        Plumber --> RegexEngine[Regex Rule Engine & Normalizers]
        OCR --> RegexEngine
        RegexEngine -->|Unstructured / Low Confidence| LLMFallback[OpenAI Structured Output Fallback]
        RegexEngine --> Reconcile[Financial Tax Reconciliation]
        LLMFallback --> Reconcile
    end

    subgraph Persistence Layer
        Reconcile --> Repository[SQLAlchemy InvoiceRepository]
        Repository --> DB[(SQLite / PostgreSQL Database)]
    end

    subgraph Export Engine
        Router -->|POST /api/export-excel| ExcelGen[openpyxl Excel Generator]
        ExcelGen -->|Workbook Stream| Client
    end

    subgraph Observability & Telemetry
        Middleware -.-> JSONLogs[Structured JSON Logger]
        Middleware -.-> Metrics[Prometheus Metrics Engine]
        Middleware -.-> Sentry[Sentry Error Tracking]
    end
```

---

## 2. Core Modules & Component Responsibilities

| Module | Responsibility | Key Classes & Functions |
| :--- | :--- | :--- |
| [`main.py`](file:///c:/Users/hflor/Downloads/Pruebas/main.py) | API gateway, route orchestration, CORS, static UI delivery. | `app`, `health_check`, `extract_invoices`, `export_excel`, `get_prometheus_metrics`. |
| [`extractor/`](file:///c:/Users/hflor/Downloads/Pruebas/extractor) | Modular package (`normalizers`, `ocr`, `llm`, `engine`, `pipeline`). | `extract_invoice_from_pdf`, `normalize_amount`, `normalize_date`, `extract_with_llm`, `RegexExtractor`. |
| [`database.py`](file:///c:/Users/hflor/Downloads/Pruebas/database.py) | Persistence layer, ORM models, session management. | `InvoiceRecord`, `InvoiceRepository`, `get_db`, `init_db`. |
| [`excel_generator.py`](file:///c:/Users/hflor/Downloads/Pruebas/excel_generator.py) | Styled Excel spreadsheet generation with formulas. | `generate_invoice_excel`. |
| [`observability.py`](file:///c:/Users/hflor/Downloads/Pruebas/observability.py) | Correlation ID tracing, Prometheus exposition, JSON logging. | `ObservabilityAndSecurityMiddleware`, `SystemMetrics`, `StructuredJsonFormatter`. |
| [`schemas.py`](file:///c:/Users/hflor/Downloads/Pruebas/schemas.py) | Pydantic v2 data contracts, boundary validation schemas. | `InvoiceData`, `BatchExtractResponse`, `ExportExcelRequest`. |

---

## 3. Extraction Pipeline Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI Router
    participant Ext as Extractor Pipeline
    participant DB as SQLite ORM
    participant Sentry as Sentry Telemetry

    User->>API: POST /api/extract (multipart/form-data)
    Note over API: Validates file extension & 25MB ceiling
    API->>Ext: extract_invoice_from_pdf(pdf_bytes, filename)
    Ext->>Ext: Try pdfplumber extraction
    alt Text is empty (scanned image)
        Ext->>Ext: pdf2image + pytesseract OCR
    end
    Ext->>Ext: Regex patterns (Tax IDs: RFC, RUT, NIF, CIF, RUC, CNPJ)
    Ext->>Ext: Currency parser (USD, EUR, MXN, COP, CLP, BRL, GBP)
    alt Fields incomplete & OPENAI_API_KEY present
        Ext->>Ext: OpenAI Structured Output fallback
    end
    Ext->>Ext: Tax reconciliation (Subtotal + Tax = Total)
    Ext-->>API: InvoiceData object
    API->>DB: InvoiceRepository.save(invoice)
    DB-->>API: InvoiceRecord persisted
    API-->>User: 200 OK (BatchExtractResponse)
    opt Unhandled Exception
        API->>Sentry: sentry_sdk.capture_exception(exc)
        API-->>User: 500 Internal Error (Sanitized JSON)
    end
```

---

## 4. Multi-Currency Normalization

The normalization engine handles complex regional formatting conventions:

1. **Anglo-Saxon Notation:** `1,234.50` -> comma as thousand separator, period as decimal separator.
2. **European / South American Notation:** `1.234,50 €` / `R$ 4.500,75` -> period as thousand separator, comma as decimal separator.
3. **Chilean Peso (CLP):** Non-decimal whole units `CLP $ 850.000` -> normalized to `850000.0`.
4. **Auto-Reconciliation:** If subtotal and total are detected but tax amount is missing, tax is mathematically reconciled as `round(total - subtotal, 2)` with standard tax rate verification.

---

## 5. Telemetry & Metrics Design

The service provides dual observability endpoints:

1. **`GET /api/metrics` (JSON):** Real-time JSON snapshot intended for internal health dashboards and quick polling.
2. **`GET /metrics` (Prometheus text format):** Standard OpenMetrics endpoint intended for Prometheus server scraping and Grafana visualization, providing:
   - `invoicetosheet_http_requests_total` (counter)
   - `invoicetosheet_invoices_processed_total{status="success|warning|error"}` (counter)
   - `invoicetosheet_excels_generated_total` (counter)
   - `invoicetosheet_unhandled_errors_total` (counter)
   - `invoicetosheet_uptime_seconds` (gauge)
