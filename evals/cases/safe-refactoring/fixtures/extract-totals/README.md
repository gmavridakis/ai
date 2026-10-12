# ledger-export

Monthly CSV export used by finance. The CSV must stay byte-identical across releases: finance diffs the files.

Run the suite with `python -m unittest discover -s tests -v` (stdlib only, no packages).
