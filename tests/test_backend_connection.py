import pytest

import app as app_module
from database import db, queries


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def _new_user(client):
    client.post("/register", data={"name": "New Person", "email": "new@x.com", "password": "password1"})
    return _login(client, "new@x.com", "password1")


# ---- query helpers ---------------------------------------------------- #

def test_get_user_by_id(client):
    user = queries.get_user_by_id(1)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert len(user["member_since"].split()) == 2


def test_get_user_by_id_missing(client):
    assert queries.get_user_by_id(999) is None


def test_summary_stats(client):
    stats = queries.get_summary_stats(1)
    assert stats["total_spent"] == pytest.approx(3899.0)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_empty(client):
    assert queries.get_summary_stats(999) == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_recent_transactions(client):
    rows = queries.get_recent_transactions(1)
    assert len(rows) == 8
    assert [r["date"] for r in rows] == sorted((r["date"] for r in rows), reverse=True)
    assert set(rows[0]) == {"date", "description", "category", "amount"}


def test_recent_transactions_empty(client):
    assert queries.get_recent_transactions(999) == []


def test_category_breakdown(client):
    rows = queries.get_category_breakdown(1)
    assert len(rows) == 7
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(r["pct"], int) for r in rows)
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_empty(client):
    assert queries.get_category_breakdown(999) == []


# ---- route ------------------------------------------------------------ #

def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_seed_user(client):
    _login(client)
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Demo User" in html and "demo@spendly.com" in html
    assert "₹3,899.00" in html
    assert "Bills" in html
    # newest first
    assert html.index("Lunch out") < html.index("Groceries")
    for cat in db.CATEGORIES:
        assert cat in html


def test_profile_new_user_empty(client):
    _new_user(client)
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "₹0.00" in html
    assert "New Person" in html


def test_profile_deleted_user_redirects(client):
    _login(client)
    conn = db.get_db()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
