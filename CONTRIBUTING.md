# Contributing to TextHumanize

Thank you for considering a contribution! This guide covers the process.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Full test suite
pytest tests/ -q

# Single file
pytest tests/test_core.py -q

# With coverage
pytest tests/ --cov=texthumanize --cov-report=term-missing
```

## Linting

We use **ruff** for linting and formatting:

```bash
ruff check texthumanize/ tests/
ruff format --check texthumanize/ tests/
```

## Type Checking

```bash
mypy texthumanize/ --ignore-missing-imports
```

## Project Structure

```
texthumanize/          # Main package
├── __init__.py        # Public API (PEP 562 lazy loading)
├── core.py            # humanize(), detect_ai(), and other top-level functions
├── pipeline.py        # 17-stage processing pipeline
├── exceptions.py      # Exception hierarchy
├── lang/              # Language-specific dictionaries (RU, EN, DE, FR, ES, …)
├── detectors.py       # AI detection heuristics
└── ...                # 60+ specialized modules
tests/                 # pytest test suite (1700+ tests)
php/                   # PHP port
examples/              # Usage examples
docs/                  # Documentation (if present)
```

## Pull Request Guidelines

1. **Create a branch** from `main`.
2. **Write tests** for any new functionality.
3. **Run the full test suite** before submitting.
4. **Keep PRs focused** — one feature or fix per PR.
5. **Update CHANGELOG.md** if your change is user-facing.
6. **Follow existing code style** — English docstrings, type hints for public APIs.

## Adding a New Language

1. Create `texthumanize/lang/<code>.py` with synonyms, collocations, and fillers.
2. Register the language in `texthumanize/lang/__init__.py`.
3. Add tests in `tests/test_multilang.py`.

## Reporting Bugs

Open an issue with:
- Python version
- `texthumanize` version (`python -c "import texthumanize; print(texthumanize.__version__)"`)
- Minimal reproducible example
- Expected vs actual behavior

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
