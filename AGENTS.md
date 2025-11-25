# Rule file for cursor (**MUST FOLLOW**)

## Desing Guide (**MUST FOLLOW**)

Guide line is in [DESIGN.md](./DESIGN.md)

## Rules for executing python file and managing python enviornment

- Use `uv` as python package manager.
- Use `uv sync` command to create a virtual environment and install dependencies.
- Alwasy activate [.venv](./.venv) using `source ./.venv/bin/acitvate` for linux system.
- Use `uv add` command to install python packages.
- Use `uv run` command to run python scripts.
- Use [pyproject.toml](./pyproject.toml) instead of requirements.txt files.

## Rules for unit tests

### fixture classification

- Define global fixtures in [conftest.py](./test/conftest.py) for use across all tests.
- Define module-specific fixtures in `conftest.py` for tests within a module. e.g fixuture for tests from [app](./test/app) puts in [conftest.py](./test/app/conftest.py) which are only use for tests of app module.
- Define file-specific fixtures within the test file if they are only used there.

## Database

- Use sqlalchemy async functionality.
- Always use sqlalchemy 2.0 syntax.
- Mindfull about that in future planning to use postgres database, but for now using sqlite database.

## Current Goal

1. Make frontend working with backend.
2. Restructure codebase as per design guide.
3. Implement missing functionality in codebase according to design guide.
