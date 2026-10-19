"""Validate customer rows before insert. Called by the import command and the upload endpoint."""
import csv
import sys
from datetime import datetime

COLUMNS = ["name", "email", "birth_date", "credit_limit"]


def validate_row(row):
    """Return the cleaned row or raise ValueError on the first problem."""
    if not row.get("name"):
        raise ValueError("name is required")
    if len(row["name"]) > 80:
        raise ValueError("name too long")
    if "@" not in row.get("email", ""):
        raise ValueError("bad email")
    try:
        birth = datetime.strptime(row["birth_date"][:10], "%Y-%m-%d")
    except Exception:
        birth = None
    credit = row.get("credit_limit") or 0
    return {
        "name": row["name"],
        "email": row["email"].lower(),
        "birth_date": birth,
        "credit_limit": int(float(credit)),
    }


def validate_file(path):
    with open(path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=1):
            try:
                validate_row(row)
                print(f"ok {i}")
            except ValueError as exc:
                print(f"error {i} {exc}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(validate_file(sys.argv[1]))
