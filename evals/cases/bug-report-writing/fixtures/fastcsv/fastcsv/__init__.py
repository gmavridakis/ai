"""fastcsv 3.2.0 (vendored copy of the upstream package for reproduction)."""
__version__ = "3.2.0"
import csv as _csv


def read(path, encoding=None):
    # 3.2.0 changed the default from latin-1 to utf-8 (see CHANGELOG)
    enc = encoding or "utf-8"
    with open(path, encoding=enc, newline="") as fh:
        return list(_csv.DictReader(fh))
