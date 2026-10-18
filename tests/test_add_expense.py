from datetime import date, timedelta

import pytest

import app as app_module
from database import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _login(client):
    return client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})


def _expense_count():
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


def _valid(**overrides):
    data = {
        "amount": "250.50",
        "category": "Food",
        "date": date.today().isoformat(),
        "description": "Dinner",
    }
    data.update(overrides)
    return data


# ---- auth ------------------------------------------------------------- #

def test_get_logged_out_redirects_to_login(client):
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_logged_out_redirects_and_saves_nothing(client):
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid())
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert _expense_count() == before


# ---- form ------------------------------------------------------------- #

def test_get_renders_form_with_all_categories(client):
    _login(client)
    resp = client.get("/expenses/add")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for category in db.CATEGORIES:
        assert f'value="{category}"' in html
    assert date.today().isoformat() in html


# ---- success ---------------------------------------------------------- #

def test_valid_post_saves_and_redirects_to_profile(client):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid())
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]
    assert _expense_count() == before + 1

    conn = db.get_db()
    row = conn.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row["user_id"] == 1
    assert row["amount"] == pytest.approx(250.5)
    assert row["category"] == "Food"
    assert row["description"] == "Dinner"


def test_new_expense_appears_on_profile(client):
    _login(client)
    client.post("/expenses/add", data=_valid(description="Unique-marker-expense"))
    html = client.get("/profile").get_data(as_text=True)
    assert "Unique-marker-expense" in html


def test_blank_description_is_accepted(client):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid(description=""))
    assert resp.status_code == 302
    assert _expense_count() == before + 1


# ---- validation ------------------------------------------------------- #

@pytest.mark.parametrize("amount", ["", "0", "-5", "abc", "nan", "inf"])
def test_invalid_amount_rejected(client, amount):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid(amount=amount))
    assert resp.status_code == 200
    assert 'role="alert"' in resp.get_data(as_text=True)
    assert _expense_count() == before


def test_invalid_category_rejected(client):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid(category="Hacking"))
    assert resp.status_code == 200
    assert 'role="alert"' in resp.get_data(as_text=True)
    assert _expense_count() == before


@pytest.mark.parametrize("bad_date", ["", "garbage", "2025-13-45"])
def test_invalid_date_rejected(client, bad_date):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid(date=bad_date))
    assert resp.status_code == 200
    assert 'role="alert"' in resp.get_data(as_text=True)
    assert _expense_count() == before


def test_future_date_rejected(client):
    _login(client)
    before = _expense_count()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = client.post("/expenses/add", data=_valid(date=tomorrow))
    assert resp.status_code == 200
    assert "future" in resp.get_data(as_text=True)
    assert _expense_count() == before


def test_long_description_rejected(client):
    _login(client)
    before = _expense_count()
    resp = client.post("/expenses/add", data=_valid(description="x" * 201))
    assert resp.status_code == 200
    assert "200" in resp.get_data(as_text=True)
    assert _expense_count() == before


def test_values_preserved_after_error(client):
    _login(client)
    resp = client.post(
        "/expenses/add",
        data=_valid(amount="-5", category="Health", description="Keep me"),
    )
    html = resp.get_data(as_text=True)
    assert 'value="-5"' in html
    assert "Keep me" in html
    assert 'value="Health" selected' in html
