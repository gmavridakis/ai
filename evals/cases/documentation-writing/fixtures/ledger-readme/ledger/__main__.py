import sys
from pathlib import Path

from ledger import config
from ledger.core import summarise


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "summarise":
        print("usage: python -m ledger summarise <file.csv>")
        return 2
    config.api_key()
    path = argv[1] if Path(argv[1]).exists() else str(Path(config.data_dir()) / argv[1])
    count, total = summarise(path)
    print(f"{count} entries, total {total:.2f} {config.currency()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
