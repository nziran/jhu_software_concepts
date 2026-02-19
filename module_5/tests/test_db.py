import pytest
pytestmark = pytest.mark.db
import src.db as dbmod

def test_connect_db_raises_when_required_env_missing(monkeypatch):
    # Ensure DATABASE_URL is not used
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Remove required DB_* vars
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(RuntimeError) as exc:
        dbmod.connect_db()

    assert "Missing required DB env vars" in str(exc.value)

def test_connect_db_uses_database_url(monkeypatch):
    # Force DATABASE_URL path (covers db_url branch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://someone@localhost:5432/gradcafe")

    called = {"args": None, "kwargs": None}

    def fake_connect(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs

        class FakeConn:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): return False

        return FakeConn()

    monkeypatch.setattr(dbmod.psycopg, "connect", fake_connect)

    with dbmod.connect_db():
        pass

    assert called["args"] == ("postgresql://someone@localhost:5432/gradcafe",)
    assert called["kwargs"] == {}


def test_connect_db_uses_parts_and_password(monkeypatch):
    # Force DB_* path + password present (covers password branch + int(port))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "gradcafe")
    monkeypatch.setenv("DB_USER", "app_user")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    called = {"args": None, "kwargs": None}

    def fake_connect(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs

        class FakeConn:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): return False

        return FakeConn()

    monkeypatch.setattr(dbmod.psycopg, "connect", fake_connect)

    with dbmod.connect_db():
        pass

    assert called["args"] == ()
    assert called["kwargs"]["host"] == "localhost"
    assert called["kwargs"]["port"] == 5432
    assert called["kwargs"]["dbname"] == "gradcafe"
    assert called["kwargs"]["user"] == "app_user"
    assert called["kwargs"]["password"] == "secret"
