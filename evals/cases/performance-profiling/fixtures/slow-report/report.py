"""Monthly revenue per customer tier. Run: python report.py [month]"""
import sys
from collections import defaultdict

import db


def build_report(month):
    orders = [o for o in db.load_orders() if o["month"] == month]
    revenue_by_tier = defaultdict(float)
    for order in orders:
        customer = db.fetch_customer(order["customer_id"])
        tier = customer["tier"] if customer else "unknown"
        revenue_by_tier[tier] += order["amount"]
    return dict(sorted(revenue_by_tier.items()))


def main():
    month = sys.argv[1] if len(sys.argv) > 1 else "2026-09"
    report = build_report(month)
    for tier, amount in report.items():
        print(f"{tier:<10} {amount:>12.2f}")
    print(f"db calls: {db.CALLS}", file=sys.stderr)


if __name__ == "__main__":
    main()
