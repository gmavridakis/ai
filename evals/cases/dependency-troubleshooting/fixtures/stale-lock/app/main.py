"""Monthly invoice batch: reads invoices/<month>.json and renders the summary table."""
import json
import sys
from pathlib import Path

from reportlib import render_table  # render_table exists since reportlib 2.0
from tabulate import tabulate


def load(month: str) -> list[dict]:
    return json.loads(Path("invoices", f"{month}.json").read_text())


def main(month: str) -> None:
    rows = load(month)
    print(tabulate([[r["id"], r["total"]] for r in rows], headers=["id", "total"]))
    print(render_table(rows, columns=["id", "customer", "total"]))


if __name__ == "__main__":
    main(sys.argv[1])
