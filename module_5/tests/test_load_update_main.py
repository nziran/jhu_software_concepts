import json
import runpy
import sys
import types
import pytest


class _FakeCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return (0,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    def commit(self):
        return None

    def rollback(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.db
def test_load_update_main_runs(tmp_path, monkeypatch):
    # Make the expected input file exist (even if empty)
    (tmp_path / "cleaned_applicant_data_update.json").write_text("[]", encoding="utf-8")

    # Ensure any relative paths in the script resolve here
    monkeypatch.chdir(tmp_path)

    # Fake psycopg module so running __main__ can't touch a real DB
    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **k: _FakeConn())
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    # Run the module like: python -m src.load_update
    runpy.run_module("src.load_update", run_name="__main__")