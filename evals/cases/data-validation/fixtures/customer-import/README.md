# customer-import

Loads `samples/customers.csv` into the customers table (Postgres, `name VARCHAR(80)`, `email VARCHAR(254)`, `birth_date DATE`, `credit_limit INTEGER`).

Run: `python -m importer.validate samples/customers.csv` prints one line per row: `ok <row>` or `error <row> <reason>`.
Tests: `python -m unittest discover -s tests -t .` (unittest only; pytest and hypothesis are not installed).

Known complaints from support: rows with accented names sometimes appear twice in search, a customer with an emoji name broke the profile page, one file "with a wrong February date" was imported anyway, and the importer stops at the first bad row so people fix files one error at a time.
