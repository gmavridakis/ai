import sys
names = [f"test_{m}_{i}" for m in ("orders", "users", "billing", "auth") for i in range(1, 76)]
fails = {"test_orders_12": "AssertionError: expected 200, received 500 (orders.py:88)",
         "test_orders_19": "ConnectionRefusedError: [Errno 111] 127.0.0.1:5432",
         "test_billing_3": "ConnectionRefusedError: [Errno 111] 127.0.0.1:5432"}
for n in names:
    if n in fails:
        print(f"FAIL {n}\n    {fails[n]}")
    else:
        print(f"PASS {n} (0.0{len(n) % 9}s)")
print(f"\n{len(names) - len(fails)} passed, {len(fails)} failed in 4.1s")
sys.exit(1)
