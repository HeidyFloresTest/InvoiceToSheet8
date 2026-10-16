# Security Policy

## Supported Versions

We provide security updates and patches for the following versions of **InvoiceToSheet**:

| Version | Supported          |
| ------- | ------------------ |
| 1.4.x   | :white_check_mark: |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :x:                |

---

## Reporting a Vulnerability

The InvoiceToSheet engineering team takes product security seriously. If you believe you have discovered a security vulnerability in this microservice, please report it responsibly:

1. **Do NOT open a public GitHub issue** with sensitive vulnerability reproduction details.
2. Submit your findings via email to: **heidyflores@users.noreply.github.com** with the subject line `[SECURITY] Potential Vulnerability in InvoiceToSheet`.
3. Include the following details to help triage and reproduce:
   - Type of vulnerability (e.g., path traversal, SSRF, injection, secrets disclosure).
   - Step-by-step reproduction guide with minimal payload or curl command.
   - Impact assessment and potential attack vectors.
   - Proposed mitigation or patch (if available).

### Response SLA & Timeline
- **Initial Acknowledgment:** Within 48 hours of report submission.
- **Triage & Reproduction:** Within 5 business days.
- **Fix & Disclosure:** Patch released within 14 business days, followed by coordinated advisory.

---

## Production Secret Provisioning & Key Rotation Protocol

InvoiceToSheet enforces strict separation of code and configuration, adhering to Twelve-Factor App principles and zero-trust credential hygiene:

### 1. Secret Manager Injection in Production
Plain `.env` files are strictly prohibited in production and staging environments. All sensitive credentials must be injected dynamically at runtime via a centralized Secret Manager:

| Credential | Provider Implementation Pattern | Rotation Cadence |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Injected via **HashiCorp Vault**, **AWS Secrets Manager**, or **Docker Secrets** (`/run/secrets/openai_key`). | Every 90 days or immediately upon suspected compromise. |
| `SENTRY_DSN` | Injected as environment variable from cloud platform metadata service (AWS SSM Parameter Store / GCP Secret Manager). | Annual or per environment lifecycle change. |
| `DATABASE_URL` | Dynamic database credential leasing via HashiCorp Vault database secrets engine or AWS IAM RDS authentication. | Automated short-lived leases (24-hour TTL). |

### 2. Zero-Downtime Secret Rotation Procedure
1. **Provision Secondary Key:** Generate a new API token in the external provider dashboard (e.g., OpenAI API portal).
2. **Update Secret Vault:** Store the updated secret under the versioned secret path in the Secrets Manager.
3. **Rolling Service Restart:** Initiate a rolling restart of container tasks (`kubectl rollout restart` or `docker compose up -d`).
4. **Health Verification:** Validate that `/health` returns `"status": "healthy"` and `"database": "connected"`.
5. **Revoke Retired Key:** Permanently invalidate the deprecated credential in the provider portal.

---

## Security Practices & Design Controls

1. **Zero Secret Persistence:**
   - Secrets are loaded into memory and validated by `config.Settings` at application startup.
   - Malformed or truncated keys raise typed `ConfigurationError` immediately, failing fast before accepting traffic.
   - Automated secret redaction in logging middleware prevents leakage of credentials in error traces.

2. **Input Sanitization & Boundary Validation:**
   - Strict multipart file validation (MIME type verification, maximum size capped at 25 MB per file).
   - In-memory PDF processing via `pdfplumber` without storing temporary files on disk.
   - Pydantic v2 schemas enforce strongly-typed constraints on all payload boundaries.
   - Path traversal mitigation on file identifiers and origin headers.

3. **HTTP Hardening (OWASP Compliance):**
   - Mandatory security headers applied on all responses:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `X-XSS-Protection: 1; mode=block`
     - `Referrer-Policy: strict-origin-when-cross-origin`
   - CORS origin filtering restricted to explicit trusted domains defined in `ALLOWED_ORIGINS`.

4. **Continuous Dependency Auditing:**
   - Automated GitHub Actions CI workflow runs `pip-audit` to detect known CVEs in locked dependencies.
   - Dependabot configured for automated weekly vulnerability patches with an active PR ceiling.

---

## Threat Model & Trust Boundaries

The InvoiceToSheet microservice defines four distinct trust boundaries based on STRIDE threat modeling principles:

| Trust Boundary | Threat Vector Analyzed | Mitigations Implemented in Code |
| :--- | :--- | :--- |
| **1. Multipart File Ingestion** | Decompression bombs, memory exhaustion, malformed PDF structures | - Strict 25MB file size limit enforced prior to stream consumption.<br>- In-memory byte streaming via `pdfplumber` (zero disk write).<br>- Isolated exception handling returning typed `CorruptedPdfError`. |
| **2. External Credentials** | Accidental API key leakage via stack traces or error logs | - `OPENAI_API_KEY` and `SENTRY_DSN` loaded via environment.<br>- Automated regex masking in `ObservabilityAndSecurityMiddleware`.<br>- Dummy fallback fixture ensuring hermetic offline test execution. |
| **3. Database Persistence** | SQL injection, data corruption, unauthorized table modifications | - Declarative SQLAlchemy 2.0 ORM with parameterized SQL queries.<br>- Pydantic v2 input schema validation before persistence.<br>- SQLite / PostgreSQL transaction rollback on failure. |
| **4. Excel Export Boundary** | Formula injection (DDE attacks) via invoice text fields | - Openpyxl cell value sanitization preventing leading `=,+,-,@` formulas.<br>- Typed float formatting for numeric amount cells.<br>- Dynamic SUM formulas restricted strictly to calculated summary rows. |
