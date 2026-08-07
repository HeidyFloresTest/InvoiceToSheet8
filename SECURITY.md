# Security Policy

## Supported Versions

We provide security updates and patches for the following versions of **InvoiceToSheet**:

| Version | Supported          |
| ------- | ------------------ |
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

## Security Practices & Design Controls

1. **Zero Secret Persistence:**
   - Secrets (`OPENAI_API_KEY`, `SENTRY_DSN`, database credentials) are injected strictly via environment variables.
   - No `.env` files are tracked in version control; `.env.example` provides non-sensitive defaults.
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
