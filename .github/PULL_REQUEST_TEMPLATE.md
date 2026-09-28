## Description
Briefly describe the purpose of this PR, the problem it solves, or the feature it introduces.

## Related Issues
Closes #(issue_number)

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update
- [ ] CI/CD or tooling optimization

## Testing Performed
Describe the automated tests added or executed to verify changes:
- [ ] Added unit/integration test in `tests/`
- [ ] Verified `pytest --cov=. --cov-report=term-missing` passes with coverage >= 80%
- [ ] Tested offline/hermetic execution with dummy credentials

## Quality Checklist
- [ ] My code follows the project's style guidelines (`ruff check .` passes)
- [ ] My code is strictly formatted (`ruff format --check .` passes)
- [ ] My code passes type checking (`mypy .` passes)
- [ ] I have updated corresponding documentation (`README.md`, `CHANGELOG.md`, `ARCHITECTURE.md` if applicable)
- [ ] No hardcoded credentials or sensitive data are committed
