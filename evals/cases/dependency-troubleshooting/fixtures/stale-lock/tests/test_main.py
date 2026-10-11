from app.main import load


def test_load_reads_month(tmp_path, monkeypatch):
    (tmp_path / "invoices").mkdir()
    (tmp_path / "invoices" / "2026-09.json").write_text('[{"id": 1, "customer": "acme", "total": 10}]')
    monkeypatch.chdir(tmp_path)
    assert load("2026-09")[0]["customer"] == "acme"
