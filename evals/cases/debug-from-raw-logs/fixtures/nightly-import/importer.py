"""Nightly vendor import. Usage: python importer.py data/<file>.csv"""
import csv, sys


def parse(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            if not row.get("vendor"):
                raise ValueError(f"{path}:{i}: empty vendor")
            rows.append({"vendor": row["vendor"].strip(), "amount": float(row["amount"])})
    return rows


def main(argv):
    if len(argv) != 2:
        print("usage: importer.py <csv>", file=sys.stderr)
        return 2
    rows = parse(argv[1])
    total = sum(r["amount"] for r in rows)
    print(f"imported {len(rows)} rows, total {total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
