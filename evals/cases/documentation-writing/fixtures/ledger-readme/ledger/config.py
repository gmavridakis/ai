import os


def data_dir() -> str:
    return os.environ.get("LEDGER_DATA_DIR", "data")


def currency() -> str:
    return os.environ.get("LEDGER_CURRENCY", "EUR")


def api_key() -> str:
    key = os.environ.get("LEDGER_API_KEY")
    if not key:
        raise SystemExit("Missing required setting LEDGER_API_KEY")
    return key
