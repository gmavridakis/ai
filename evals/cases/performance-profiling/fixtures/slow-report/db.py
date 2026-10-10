"""Tiny in-process "database" for the monthly report. Every call counts like a round trip."""
import json
import pathlib

DATA = pathlib.Path(__file__).parent / "data"
CALLS = {"fetch_customer": 0, "fetch_customers_by_ids": 0, "load_orders": 0}

_customers = None


def _customers_table():
    global _customers
    if _customers is None:
        _customers = json.loads((DATA / "customers.json").read_text())
    return _customers


def load_orders():
    CALLS["load_orders"] += 1
    return json.loads((DATA / "orders.json").read_text())


def fetch_customer(customer_id):
    """One customer by id: a full scan of the table, like SELECT without an index."""
    CALLS["fetch_customer"] += 1
    rows = [c for c in _customers_table() if c["id"] == customer_id]
    return rows[0] if rows else None


def fetch_customers_by_ids(ids):
    """Many customers in one call, keyed by id."""
    CALLS["fetch_customers_by_ids"] += 1
    wanted = set(ids)
    return {c["id"]: c for c in _customers_table() if c["id"] in wanted}
