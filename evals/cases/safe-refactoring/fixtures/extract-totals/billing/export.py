"""CSV export of invoice lines for one month.

export_csv() grew into validation, totals and formatting in one function.
Finance diffs the produced files month over month, so the bytes matter.
"""
import csv
import io
from datetime import date

VAT_RATES = {"EL": 0.24, "DE": 0.19, "FR": 0.20, "IT": 0.22}
ALLOWED_STATUS = ("issued", "paid", "credit")


def export_csv(rows, filters):
    # --- validate filters -------------------------------------------------
    if "month" not in filters:
        raise ValueError("month is required (YYYY-MM)")
    month = filters["month"]
    try:
        date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError("month must be YYYY-MM, got %r" % month)
    status = filters.get("status", "issued")
    if status not in ALLOWED_STATUS:
        raise ValueError("status must be one of %s" % ", ".join(ALLOWED_STATUS))
    country = filters.get("country")
    if country is not None and country not in VAT_RATES:
        raise ValueError("unknown country %r" % country)

    # --- select and total -------------------------------------------------
    selected = []
    for row in rows:
        if not row["date"].startswith(month):
            continue
        if row["status"] != status and not (status == "issued" and row["status"] == "paid"):
            continue
        if country is not None and row["country"] != country:
            continue
        selected.append(row)
    selected.sort(key=lambda r: (r["date"], r["number"]))

    totals_by_customer = {}
    grand_net = 0.0
    grand_vat = 0.0
    for row in selected:
        sign = -1 if row["status"] == "credit" else 1
        net = sign * row["net"]
        rate = VAT_RATES[row["country"]]
        vat = round(net * rate, 2)
        entry = totals_by_customer.setdefault(row["customer"], {"net": 0.0, "vat": 0.0, "lines": 0})
        entry["net"] = round(entry["net"] + net, 2)
        entry["vat"] = round(entry["vat"] + vat, 2)
        entry["lines"] += 1
        grand_net = round(grand_net + net, 2)
        grand_vat = round(grand_vat + vat, 2)

    # --- write ------------------------------------------------------------
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["number", "date", "customer", "country", "status", "net", "vat", "gross"])
    for row in selected:
        sign = -1 if row["status"] == "credit" else 1
        net = sign * row["net"]
        vat = round(net * VAT_RATES[row["country"]], 2)
        writer.writerow([
            row["number"], row["date"], row["customer"], row["country"], row["status"],
            "%.2f" % net, "%.2f" % vat, "%.2f" % round(net + vat, 2),
        ])
    writer.writerow([])
    for customer in sorted(totals_by_customer):
        entry = totals_by_customer[customer]
        writer.writerow([
            "TOTAL", "", customer, "", "%d lines" % entry["lines"],
            "%.2f" % entry["net"], "%.2f" % entry["vat"], "%.2f" % round(entry["net"] + entry["vat"], 2),
        ])
    writer.writerow([
        "GRAND", month, "", "", "%d lines" % len(selected),
        "%.2f" % grand_net, "%.2f" % grand_vat, "%.2f" % round(grand_net + grand_vat, 2),
    ])
    return out.getvalue()
