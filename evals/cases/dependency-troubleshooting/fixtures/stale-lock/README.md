# invoice-batch

Monthly invoice summary. `python -m app.main 2026-09` renders the table for a month.

Install from the lock: `pip install -r requirements.lock` then `pip install -e .[dev] --no-deps`. The lock is produced by `pip-compile --output-file=requirements.lock pyproject.toml`.

There is no network from this workspace and `pip-compile` is not installed: `captures/` holds the CI log of the failing run (8842), the CI `pip check` output, and a snapshot of the developer's working environment.
