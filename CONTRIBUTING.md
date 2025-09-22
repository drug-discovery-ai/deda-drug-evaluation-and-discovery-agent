# Contributing Guidelines

Welcome to DEDA.

## Getting Started

We have full documentation on how to get started contributing here:

### Code Quality

This project uses `ruff` for linting and formatting, and `mypy` for type checking.

### Development Setup

Install development dependencies:

```bash
pip install -e ".[dev]"
pre-commit install
```

The `pre-commit install` sets up Git hooks to automatically run `ruff`, `mypy`, and `pytest` before each commit,
preventing broken code from reaching the repository.

Run linting:

```bash
ruff check .          # Check for linting issues
ruff check . --fix    # Auto-fix linting issues
ruff format .         # Auto-format code
```

Run type checking:

```bash
mypy .                # Run type checking on all files
```

## Testing

The project includes a unified snapshot testing system for reliable, fast API testing:

### Run Tests

```bash
# Run all tests (uses snapshots by default - fast, no network calls)
pytest

# Run only unit tests (uses mocks)
pytest -k "unit"

# Run only integration tests (uses snapshots)  
pytest -k "integration"

# Update snapshots from live APIs (when APIs change)
pytest --update-snapshots

# Validate existing snapshots against live APIs
pytest --validate-snapshots
```

### Test Architecture

- **Unit tests**: Use `@patch` decorators for fast, isolated testing
- **Integration tests**: Use `@pytest.mark.integration` with automatic snapshot/recording
- **Snapshots**: Real API responses captured for realistic testing without network calls
- **HTTP Interception**: Transparent to application code - no changes needed to API clients

See `snapshots/README.md` for detailed information about the snapshot testing system.