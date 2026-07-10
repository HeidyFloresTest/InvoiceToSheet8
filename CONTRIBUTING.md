# Contributing to InvoiceToSheet

Thank you for your interest in contributing to **InvoiceToSheet**! We welcome bug reports, feature requests, and pull requests.

## Development Workflow

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HeidyFloresTest/InvoiceToSheet1.git
   cd InvoiceToSheet1
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
   All features or bug fixes must include corresponding tests. The overall test coverage must remain above **85%**:
   ```bash
   pytest --cov=. --cov-report=term-missing
   ```

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

## Pull Request Guidelines

1. Create a focused branch (`feat/your-feature-name` or `fix/your-fix-name`).
2. Ship changes together with their tests in atomic commits.
3. Verify all checks pass locally before opening a PR.
4. Ensure your PR description clearly describes the problem and solution.
