import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.parser import parse_amount


def test_parse_amount():
    assert parse_amount("Total: 12.50 EUR") == (12.5, "EUR")
    assert parse_amount("1,250.00 EUR") == (1250.0, "EUR")


if __name__ == "__main__":
    test_parse_amount()
    print("ok")
