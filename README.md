# SecretGuard

SecretGuard is a Python CLI project for secure secret management and automation.

## Project structure

- `main.py` — entry point for the CLI application
- `src/cli.py` — CLI commands and logging setup
- `core/` — project core package
- `configs/` — configuration files and templates
- `logs/` — generated runtime logs
- `tests/` — unit and integration tests

## Getting started

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate it:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the CLI:
   ```bash
   python main.py --help
   ```

## CLI

The project exposes a `SecretGuard` CLI with a version command:

```bash
python main.py --version
```

## Formatting and linting

- `black` for code formatting
- `flake8` for linting
