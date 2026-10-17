import pytest

import app as app_module
from database import db, queries


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    # Replace seed expenses with fixed-date rows so tests don't depend on today's date.
    conn = db.get_db()
    conn.execute("DELETE FROM expenses")
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (1, ?, ?, ?, ?)",
        [
            (100.0, "Food", "2025-01-05", "Early food"),
            (200.0, "Bills", "2025-01-10", "Mid bills"),
            (300.0, "Food", "2025-01-20", "Late food"),
            (400.0, "Health", "2025-02-01", "Feb health"),
        ],
    )
    conn.commit()
    conn.close()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _login(client):
    return client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})


# ---- query helpers ---------------------------------------------------- #

def test_no_filter_returns_everything(client):
    assert queries.get_summary_stats(1)["transaction_count"] == 4
    assert len(queries.get_recent_transactions(1)) == 4


def test_range_is_inclusive_on_both_ends(client):
    stats = queries.get_summary_stats(1, "2025-01-05", "2025-01-10")
    assert stats["transaction_count"] == 2
    assert stats["total_spent"] == pytest.approx(300.0)


def test_only_from(client):
    stats = queries.get_summary_stats(1, date_from="2025-01-20")
    assert stats["transaction_count"] == 2
    assert stats["total_spent"] == pytest.approx(700.0)


def test_only_to(client):
    stats = queries.get_summary_stats(1, date_to="2025-01-10")
    assert stats["transaction_count"] == 2


def test_empty_range(client):
    assert queries.get_summary_stats(1, "2030-01-01", "2030-12-31") == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—",
    }
    assert queries.get_recent_transactions(1, date_from="2030-01-01") == []
    assert queries.get_category_breakdown(1, date_from="2030-01-01") == []


def test_top_category_respects_range(client):
    assert queries.get_summary_stats(1)["top_category"] == "Food"
    assert queries.get_summary_stats(1, date_from="2025-02-01")["top_category"] == "Health"


def test_transactions_filtered_and_ordered(client):
    rows = queries.get_recent_transactions(1, date_from="2025-01-10", date_to="2025-01-31")
    assert [r["date"] for r in rows] == ["2025-01-20", "2025-01-10"]


def test_breakdown_filtered_pct_sums_to_100(client):
    cats = queries.get_category_breakdown(1, "2025-01-01", "2025-01-31")
    assert {c["name"] for c in cats} == {"Food", "Bills"}
    assert sum(c["pct"] for c in cats) == 100


# ---- route ------------------------------------------------------------ #

def test_profile_filter_requires_login(client):
    resp = client.get("/profile?date_from=2025-01-01")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_valid_range(client):
    _login(client)
    resp = client.get("/profile?date_from=2025-01-05&date_to=2025-01-10")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "₹300.00" in html
    assert "Mid bills" in html
    assert "Feb health" not in html
    assert 'value="2025-01-05"' in html
    assert 'value="2025-01-10"' in html


def test_profile_empty_range(client):
    _login(client)
    html = client.get("/profile?date_from=2030-01-01").get_data(as_text=True)
    assert "₹0.00" in html
    assert "No expenses in this range." in html


def test_profile_unfiltered_empty_state_text(client):
    _login(client)
    conn = db.get_db()
    conn.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()
    assert "No expenses yet." in client.get("/profile").get_data(as_text=True)


def test_profile_invalid_date_shows_error(client):
    _login(client)
    resp = client.get("/profile?date_from=garbage")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Please enter valid dates." in html
    assert "₹1,000.00" in html


def test_profile_reversed_range_shows_error_and_unfiltered(client):
    _login(client)
    html = client.get("/profile?date_from=2025-02-01&date_to=2025-01-01").get_data(as_text=True)
    assert "Start date must be on or before end date." in html
    assert "₹1,000.00" in html


def test_non_padded_date_is_normalised(client):
    _login(client)
    html = client.get("/profile?date_from=2025-1-10&date_to=2025-1-20").get_data(as_text=True)
    assert 'value="2025-01-10"' in html
    assert 'value="2025-01-20"' in html
    assert "Mid bills" in html
    assert "Early food" not in html
    assert "Feb health" not in html
