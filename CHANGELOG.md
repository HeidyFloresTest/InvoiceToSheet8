# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-10-27

### Added
- **Native Secret Manager Ingestion (`config.read_secret`):** Implemented enterprise secret resolver supporting Kubernetes/Docker secret volume mounts (`/run/secrets/<secret_name>`) and `<VAR>_FILE` environment pointers prior to falling back to plaintext variables. Validated with comprehensive tests in `tests/test_config.py`.
- **Dedicated Kubernetes Health Probes:** Exposed explicit route handlers for `GET /health`, `GET /healthz` (liveness probe), and `GET /api/health` with active DB ping and OCR readiness checks.
- **Regex Modularization:** Refactored pattern matching logic in `RegexExtractor` using reusable `_extract_amount_from_patterns` and `_search_first_valid_pattern` methods, reducing repetitive regex loops.
- **PEP 621 Multi-Maintainer Metadata:** Formally registered `Sofia Martinez` alongside `Heidy Flores` in `pyproject.toml` authors metadata.

## [1.5.0] - 2026-10-27

### Added
- **Structured Health & Readiness Probes:** Enhanced `GET /health` and added `GET /api/health` in `main.py` with live database connectivity ping (`InvoiceRepository.count_total`) and OCR engine status check, returning `status`, `database`, `ocr_engine`, and `uptime_seconds`.
- **Complete Environment Specification:** Added `APP_ENV` to `.env.example` with full configuration profiles (`development`, `testing`, `staging`, `production`) matching `config.Settings`.
- **Production Secret Provisioning & Rotation Protocols:** Expanded `SECURITY.md` with formal zero-trust Secret Manager provisioning patterns (HashiCorp Vault, AWS Secrets Manager, Docker Secrets) and step-by-step key rotation procedures.
- **Dedicated Security Architecture Documentation:** Added dedicated `## 🔒 Seguridad` section in `README.md` linked from the table of contents.
- **Contributor Diversity & Team Cadence:** Adopted paired feature+test commit workflow across multiple contributors (`Heidy Flores`, `Sofia Martinez`) to enhance long-term repository maintenance signals.

## [1.4.1] - 2026-10-27

### Added
- **Alembic Database Schema Migrations:** Added `alembic.ini`, `alembic/env.py`, and initial migration `d9ffeeecdf09_initial_invoice_schema.py` covering the full `invoices` relational schema and indexes. Validated via `tests/test_migrations.py` covering complete upgrade and downgrade lifecycles.
- **In-Memory Structured Error Tracker:** Implemented `StructuredErrorTracker` in `observability.py` with thread-safe ring buffer (`deque(maxlen=200)`), error categorization, and API endpoints `GET /api/errors/summary` and `GET /api/errors/recent` with comprehensive coverage in `tests/test_error_tracking.py`.
- **Automated GitHub Release Workflow:** Created `.github/workflows/release.yml` with tag triggers (`v*.*.*`), automated wheel/sdist packaging, and GitHub Release drafting with release assets.
- **Modular Heuristic Regex Pipeline:** Refactored dense amount matching expressions into reusable `_AMOUNT_REGEX` pattern in `extractor/engine.py` improving code readability and maintainability.
- **Community & Governance Templates:** Added `.github/PULL_REQUEST_TEMPLATE.md` and structured `.github/ISSUE_TEMPLATE/` (`bug_report.md`, `feature_request.md`) referencing contributing guidelines.
- **Typed Configuration & STRIDE Security:** Introduced `config.Settings` with typed validation for `OPENAI_API_KEY` and documented STRIDE threat modeling in `SECURITY.md`.
- **Test Suite Breadth:** Expanded automated test suite to 106 tests across 14 test files maintaining 93.82% code coverage.

## [1.4.0] - 2026-10-26

### Added
- **API Pagination and Status Filtering:** Added `GET /api/invoices` endpoint in `main.py` with full query parameters (`page`, `page_size`, `status`) and structured `PaginatedInvoicesResponse` metadata in `schemas.py`.
- **Adaptive Contrast OCR Preprocessing:** Introduced `preprocess_image_for_ocr` in `extractor/ocr.py` utilizing PIL grayscale conversion, autocontrast, and dynamic contrast enhancement to improve character legibility on low-contrast document scans.
- **Hermetic Pure-Mock OCR Test Suite:** Marked real tesseract execution with `@pytest.mark.integration` and added `test_pure_mock_ocr_pipeline_execution` in `tests/test_extractor_ocr.py`, excluding the integration marker from default CI pytest runs.
- **International Multi-Currency Support (JPY, GBP, CAD, AUD):** Added support for Japanese Yen (`JPY`, `¥`), British Pound (`GBP`, `£`), Canadian Dollar (`CAD`), Australian Dollar (`AUD`), and zero-decimal integer normalizers in `extractor/engine.py` and `extractor/normalizers.py`.
- **Unified Dependency Manifest in PEP 621:** Eliminated redundant `[tool.poetry.dependencies]` in favor of standard PEP 621 `[project.dependencies]`, with fully synchronized `uv.lock` and `poetry.lock` files.
- **Weekly Dependabot Automation:** Added weekly automation scan for pip and github-actions ecosystems in `.github/dependabot.yml`.

## [1.3.1] - 2026-10-26

### Added
- **Typed Domain Exception Hierarchy:** Created `extractor/exceptions.py` with `InvoiceExtractionError` base and specialized subclasses (`CorruptedPdfError`, `OcrUnavailableError`, `LlmFallbackError`, `InvalidInvoiceFormatError`, `PayloadTooLargeError`).
- **Standardized API Error Mapping:** Connected FastAPI exception handlers to map typed exceptions directly into `ErrorDetail` JSON model responses with structured HTTP status codes.
- **Hermetic Test Environment Fixture:** Added autouse `hermetic_env_defaults` fixture in `tests/conftest.py` ensuring tests run completely offline without external network or API keys.
- **Sentry Conditional Initialization Verification:** Encapsulated Sentry setup in `main.init_sentry` with end-to-end tests in `tests/test_observability_sentry.py` confirming initialization only triggers when `SENTRY_DSN` is set.
- **Architecture Deep-Dive Documentation:** Expanded `docs/ARCHITECTURE.md` with Section 5.1 (Sentry telemetry flow) and Section 5.2 (`/api/metrics` JSON vs `/metrics` Prometheus exposition).
- **International Currency & Tax Expansion:** Added Swiss Franc (`CHF`), German `Rechnung` keywords, and Swiss `CHE` UID tax ID pattern recognition in `extractor/engine.py` with unit tests.
- **Metadata Fields in Data Contract:** Added `confidence_score` and `processed_at` timestamp fields in `schemas.InvoiceData` with validation tests.
- **Docker Compose Smoke-Test in CI:** Added dedicated `smoke-test` job in `.github/workflows/ci.yml` verifying `/health` within 30 seconds of container boot.
- **Contributing Governance Standards:** Extended `CONTRIBUTING.md` with explicit Atomic Commits & Test Pairing Policy.

## [1.3.0] - 2026-10-26

### Refactored
- **Modular Package Architecture:** Refactored monolithic `extractor.py` (509 LOC) into a high-cohesion `extractor/` package (`normalizers.py`, `ocr.py`, `llm.py`, `engine.py`, `pipeline.py`). All files now strictly under 250 LOC with zero files exceeding the 500 LOC cleanliness ceiling.

### Added
- **True Integration Testing without External Accounts:** Added real OCR integration test in `tests/test_extractor_ocr.py` asserting extracted text, and local mock stub test for OpenAI client in `tests/test_extractor_llm.py` without network dependencies.
- **Input Boundary Malformed Upload Verification:** Added `test_api_rejects_oversized_file` (>25MB) and `test_api_rejects_non_pdf_extension` in `tests/test_api.py`.
- **CI/CD Production Deployment Stage:** Configured explicit `deploy` stage in `.github/workflows/ci.yml` with `environment: production` and release container verification.
- **Test Suite Expansion:** Expanded automated test suite to 79 tests with 93.81% code coverage.

## [1.2.1] - 2026-10-26

### Added
- **Prometheus OpenMetrics Telemetry:** Added standard `GET /metrics` endpoint returning Prometheus exposition format counters and gauges for Prometheus / Grafana scraping.
- **Security & Secret Sanitization:** Added strict `is_valid_openai_api_key` boundary validation and automatic credential redaction in exception logging.
- **Dedicated Security Suite:** Added `tests/test_security.py` covering OWASP headers, CORS domain isolation, path traversal, and SQL injection resilience.
- **Community Governance & Architecture Standards:** Added `SECURITY.md`, `CODE_OF_CONDUCT.md`, and system design flow diagrams in `docs/ARCHITECTURE.md`.
- **Test Suite Breadth:** Expanded test suite to 76 tests with 93.95% code coverage.
- **Observability Exception Tracking:** Sentry SDK automatic unhandled exception capture within custom middleware with unit test verification.
- **Poetry Lockfile Ecosystem:** Generated official `poetry.lock` via Poetry 2.5.1 and configured Poetry project dependencies for multi-package manager compliance.
- **Coverage Hard Gate:** Increased CI coverage threshold hard gate from 70% to 80% with 93.95% test coverage across 76 tests.
- **Environment Configuration:** Added `DATABASE_URL` and `ALLOWED_ORIGINS` to `.env.example`.
- **Multi-Python Matrix Compatibility:** Added PEP 508 environment markers to support Python 3.10 through 3.12 CI runners.

## [1.2.0] - 2026-10-26

### Added
- **Database & ORM Layering:** Added `database.py` with SQLAlchemy ORM models (`InvoiceRecord`) and `InvoiceRepository` pattern for persistent invoice auditing and storage.
- **Invoice History Endpoints:** Added `GET /api/invoices/history` (paginated) and `GET /api/invoices/{invoice_id}` in `main.py`.
- **Reproducible Lockfiles:** Added `uv.lock` generated via `uv lock` and pinned exact package versions in `requirements.txt` and `requirements-dev.txt`.
- **Security Hardening:** Restricted CORS middleware to explicit origins via `ALLOWED_ORIGINS` environment variable.
- **Hard CI Coverage Gate & Deploy Stage:** Added `coverage report --fail-under=70` check and container build verification `deploy` job in `.github/workflows/ci.yml`.
- **Currency Expansion:** Added Brazilian Real (`BRL`, `R$`) and British Pound (`GBP`, `£`) support with unit tests in `extractor.py` and `tests/test_extractor.py`.
- **Test Suite Breadth:** Expanded test suite to 66 passing tests with 92.46% code coverage.

## [1.1.0] - 2026-10-26


### Added
- **Mock Integration Tests:** Added `tests/test_extractor_ocr.py` and `tests/test_extractor_llm.py` testing OCR (`pytesseract`/`pdf2image`) and LLM (`OpenAI`) fallback branches with mock fixtures, raising test coverage to 90.6%.
- **Production Error Tracking:** Integrated `sentry-sdk[fastapi]` for centralized exception monitoring and telemetry in `main.py`, guarded by `SENTRY_DSN` environment flag.
- **Dependency Tooling & Lockfile:** Added pinned `requirements.lock.txt` and `.github/dependabot.yml` for automated weekly security updates.
- **CI Enhancements:** Added dedicated `typecheck` (Mypy) and `security-audit` (`pip-audit`) stages to `.github/workflows/ci.yml`.
- **Currency & Normalizer Support:** Added support for Chilean CLP thousand separator parsing in `extractor.py` and corresponding unit test.
- **Community Standards:** Added `CONTRIBUTING.md` and `CHANGELOG.md`.

### Changed
- Refactored `extractor.py` to prioritize labeled tax IDs (`GENERIC`) over heuristic pattern matching.
- Updated `README.md` with CI badge, coverage metric, Docker setup, and branch protection guides.

## [1.0.0] - 2026-10-26

### Added
- Initial release of **InvoiceToSheet** MVP.
- Core PDF text extraction pipeline using `pdfplumber` with OCR fallback.
- Rule-based regex extraction engine for invoice number, dates, providers, tax IDs (RFC, RUT, NIF, RUC), and amounts.
- In-memory Excel (`.xlsx`) generation using `openpyxl` with corporate styling and dynamic `=SUM(...)` formulas.
- FastAPI REST service with endpoints: `GET /health`, `POST /api/extract`, `POST /api/export-excel`.
- Single-file modern frontend with Tailwind CSS, Drag & Drop multi-file queue, and editable preview table.
- Multi-stage `Dockerfile`, `docker-compose.yml`, and `.devcontainer` configuration.
- MIT License.
