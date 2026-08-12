# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
