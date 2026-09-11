# Contributing to InvoiceToSheet

Thank you for your interest in contributing to **InvoiceToSheet**! We welcome bug reports, feature requests, and pull requests.

## Development Workflow

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HeidyFloresTest/InvoiceToSheet8.git
   cd InvoiceToSheet8
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Quality Standards

All pull requests must pass the automated CI pipeline before merging:

1. **Linting & Formatting:**
   ```bash
   ruff check .
   ruff format --check .
   ```

2. **Type Checking:**
   ```bash
   mypy .
   ```

3. **Testing & Coverage:**
   All features or bug fixes must include corresponding tests. The overall test coverage must remain at or above **70%** (enforced by the hard CI gate `coverage report --fail-under=70` in GitHub Actions):
   ```bash
   pytest --cov=. --cov-report=term-missing
   coverage report --fail-under=70
   ```
   Note: Pull requests with missing tests or dropping test coverage below 70% will automatically fail CI gating.


4. **Security Audit:**
   ```bash
   pip-audit -r requirements.txt
   ```

## Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) standard:
- `feat(...)`: A new feature
- `fix(...)`: A bug fix
- `test(...)`: Adding or refactoring tests
- `docs(...)`: Documentation updates
- `ci(...)`: Changes to CI/CD workflows
- `refactor(...)`: Code changes that neither fix a bug nor add a feature
- `chore(...)`: Maintenance tasks or dependency updates

## Atomic Commits & Test Pairing Policy

To maintain a mineable, reproducible, and transparent engineering history, we enforce the following commit granularity standards:

1. **One Logical Change Per Commit:** Every commit must represent a single, self-contained engineering change. Never bundle refactorings, formatting sweeps, and feature additions in a single commit.
2. **Mandatory Test-Pairing:** Every new feature, extractor rule, or bugfix must ship together with its proving tests in the very same commit (e.g. changes in `extractor/engine.py` paired with tests in `tests/test_extractor.py`).
3. **No Test-Less Feature Commits:** Commits adding application logic without corresponding automated tests will fail review.
4. **Hermetic Test Isolation:** Tests must run 100% offline without requiring external network connectivity, live cloud credentials, or third-party paid accounts.

## Pull Request Guidelines

1. Create a focused branch (`feat/your-feature-name` or `fix/your-fix-name`).
2. Ship changes together with their tests in atomic commits adhering to the test-pairing policy.
3. Verify all checks pass locally (`pytest`, `ruff check .`, `mypy .`) before opening a PR.
4. Ensure your PR description clearly describes the problem and solution.

