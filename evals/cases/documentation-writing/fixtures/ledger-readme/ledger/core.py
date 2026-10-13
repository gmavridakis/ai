import csv
from pathlib import Path


def summarise(path: str) -> tuple[int, float]:
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    total = round(sum(float(r["amount"]) for r in rows), 2)
    return len(rows), total
