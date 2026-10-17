"""Tests for Step 6: date-range filter on GET /profile (see spec 06)."""
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
from database import db, queries

# user 1 expenses: (amount, category, date, description)
USER1_EXPENSES = [
    (100.0, "Food", "2024-01-05", "ZqAlpha"),
    (350.0, "Bills", "2024-01-10", "ZqBravo"),
    (200.0, "Food", "2024-01-15", "ZqCharlie"),
    (400.0, "Transport", "2024-02-01", "ZqDelta"),
    (1000.0, "Other", "2024-03-01", "ZqEcho"),
]
USER2_EXPENSES = [(5000.0, "Shopping", "2024-01-10", "ZqOtherUser")]
ALL_DESCRIPTIONS = [e[3] for e in USER1_EXPENSES]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    conn = sqlite3.connect(db.DB_PATH)
    for uid, name, email in ((1, "User One", "one@x.com"), (2, "User Two", "two@x.com")):
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (uid, name, email, generate_password_hash("pw123456")),
        )
    for uid, rows in ((1, USER1_EXPENSES), (2, USER2_EXPENSES)):
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            [(uid, a, c, d, desc) for a, c, d, desc in rows],
        )
    conn.commit()
    conn.close()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def auth_client(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    return client


def _page(client, query=""):
    resp = client.get("/profile" + query)
    assert resp.status_code == 200, f"expected 200 for /profile{query}, got {resp.status_code}"
    return resp.get_data(as_text=True)


def _present(html):
    return [d for d in ALL_DESCRIPTIONS if d in html]


def _db_snapshot():
    conn = sqlite3.connect(db.DB_PATH)
    rows = conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    conn.close()
    return rows


def _has_error(html):
    low = html.lower()
    return any(w in low for w in ("invalid", "error", "must be", "before", "cannot", "not valid"))


# ---------------------------------------------------------------- auth guard

@pytest.mark.parametrize("query", [
    "",
    "?date_from=2024-01-01",
    "?date_to=2024-01-31",
    "?date_from=2024-01-01&date_to=2024-01-31",
    "?date_from=garbage",
])
def test_profile_filter_logged_out_redirects_to_login(client, query):
    resp = client.get("/profile" + query)
    assert resp.status_code == 302, "logged-out access must redirect"
    assert "/login" in resp.headers["Location"]


# ------------------------------------------------------- query helpers: stats

def test_summary_stats_no_filter_matches_all_time(client):
    stats = queries.get_summary_stats(1)
    assert stats["total_spent"] == pytest.approx(2050.0)
    assert stats["transaction_count"] == 5
    assert stats["top_category"] == "Other"


def test_summary_stats_date_range_inclusive_both_ends(client):
    stats = queries.get_summary_stats(1, date_from="2024-01-10", date_to="2024-01-15")
    assert stats["total_spent"] == pytest.approx(550.0)
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Bills"


def test_summary_stats_only_date_from(client):
    stats = queries.get_summary_stats(1, date_from="2024-02-01")
    assert stats["total_spent"] == pytest.approx(1400.0)
    assert stats["transaction_count"] == 2


def test_summary_stats_only_date_to(client):
    stats = queries.get_summary_stats(1, date_to="2024-01-10")
    assert stats["total_spent"] == pytest.approx(450.0)
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Bills"


def test_summary_stats_empty_range_returns_zeros(client):
    stats = queries.get_summary_stats(1, date_from="2025-01-01", date_to="2025-12-31")
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


def test_summary_stats_excludes_other_users(client):
    stats = queries.get_summary_stats(1, date_from="2024-01-10", date_to="2024-01-10")
    assert stats["total_spent"] == pytest.approx(350.0), "other user's expense leaked into stats"


# ------------------------------------------------- query helpers: transactions

def test_recent_transactions_filtered_range(client):
    rows = queries.get_recent_transactions(1, date_from="2024-01-05", date_to="2024-01-10")
    assert sorted(r["description"] for r in rows) == ["ZqAlpha", "ZqBravo"]


def test_recent_transactions_boundaries_inclusive(client):
    rows = queries.get_recent_transactions(1, date_from="2024-01-15", date_to="2024-01-15")
    assert [r["description"] for r in rows] == ["ZqCharlie"]


def test_recent_transactions_only_date_from_sorted_desc(client):
    rows = queries.get_recent_transactions(1, date_from="2024-02-01")
    dates = [r["date"] for r in rows]
    assert dates == ["2024-03-01", "2024-02-01"]


def test_recent_transactions_empty_range_returns_empty_list(client):
    assert queries.get_recent_transactions(1, date_from="2030-01-01") == []


def test_recent_transactions_limit_ten_within_range(tmp_path, client):
    conn = sqlite3.connect(db.DB_PATH)
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [(1, 10.0, "Food", f"2023-05-{d:02d}", f"Bulk{d}") for d in range(1, 13)],
    )
    conn.commit()
    conn.close()
    rows = queries.get_recent_transactions(1, date_from="2023-05-01", date_to="2023-05-31")
    assert len(rows) == 10, "transaction list must keep its limit of 10 within the range"
    assert rows[0]["date"] == "2023-05-12"


# ------------------------------------------------- query helpers: categories

def test_category_breakdown_filtered_only_in_range(client):
    rows = queries.get_category_breakdown(1, date_from="2024-01-01", date_to="2024-01-31")
    names = {r["name"] if "name" in r else r["category"] for r in rows}
    assert names == {"Food", "Bills"}
    assert sum(r["amount"] for r in rows) == pytest.approx(650.0)


def test_category_breakdown_filtered_pct_sums_to_100(client):
    rows = queries.get_category_breakdown(1, date_from="2024-01-01", date_to="2024-02-28")
    assert rows
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_pct_sums_to_100_awkward_thirds(client):
    conn = sqlite3.connect(db.DB_PATH)
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [(1, 100.0, c, "2022-02-02", "x") for c in ("Food", "Bills", "Health")],
    )
    conn.commit()
    conn.close()
    rows = queries.get_category_breakdown(1, date_from="2022-02-02", date_to="2022-02-02")
    assert len(rows) == 3
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_empty_range_returns_empty_list(client):
    assert queries.get_category_breakdown(1, date_from="2025-01-01", date_to="2025-01-31") == []


def test_category_breakdown_no_filter_unchanged(client):
    rows = queries.get_category_breakdown(1)
    assert len(rows) == 4
    assert sum(r["pct"] for r in rows) == 100


def test_helpers_sql_injection_in_date_is_safe(client):
    evil = "2024-01-01' OR '1'='1"
    stats = queries.get_summary_stats(1, date_from=evil)
    assert isinstance(stats, dict)
    assert len(_db_snapshot()) == 6, "data must be intact"
    # evil string is a lexical bound, not SQL: must not behave as 'match all and bypass user scope'
    assert queries.get_summary_stats(1, date_from=evil)["total_spent"] <= 2050.0


# ------------------------------------------------------------------- route

def test_profile_no_params_shows_all_data(auth_client):
    html = _page(auth_client)
    assert len(_present(html)) == 5
    assert "ZqOtherUser" not in html
    assert "2,050" in html or "2050" in html


def test_profile_valid_range_shows_only_in_range(auth_client):
    html = _page(auth_client, "?date_from=2024-01-01&date_to=2024-01-31")
    assert sorted(_present(html)) == ["ZqAlpha", "ZqBravo", "ZqCharlie"]
    assert "650.00" in html


def test_profile_range_inclusive_of_end_dates(auth_client):
    html = _page(auth_client, "?date_from=2024-01-10&date_to=2024-01-15")
    assert sorted(_present(html)) == ["ZqBravo", "ZqCharlie"]
    assert "550.00" in html


def test_profile_only_date_from(auth_client):
    html = _page(auth_client, "?date_from=2024-02-01")
    assert sorted(_present(html)) == ["ZqDelta", "ZqEcho"]
    assert "1,400.00" in html or "1400.00" in html


def test_profile_only_date_to(auth_client):
    html = _page(auth_client, "?date_to=2024-01-05")
    assert _present(html) == ["ZqAlpha"]
    assert "100.00" in html


def test_profile_filter_applies_to_category_section(auth_client):
    html = _page(auth_client, "?date_from=2024-02-01&date_to=2024-02-28")
    assert "Transport" in html
    assert "Bills" not in html, "out-of-range category must not appear in breakdown"


def test_profile_empty_range_shows_zero_state(auth_client):
    html = _page(auth_client, "?date_from=2030-01-01&date_to=2030-12-31")
    assert "₹0.00" in html
    assert "—" in html
    assert "No expenses in this range." in html
    assert _present(html) == []


def test_profile_empty_state_text_without_filter_unchanged(client):
    conn = sqlite3.connect(db.DB_PATH)
    conn.execute("DELETE FROM expenses WHERE user_id = ?", (1,))
    conn.commit()
    conn.close()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    html = _page(client)
    assert "No expenses yet." in html
    assert "No expenses in this range." not in html


def test_profile_nonempty_filtered_hides_empty_message(auth_client):
    html = _page(auth_client, "?date_from=2024-01-01&date_to=2024-01-31")
    assert "No expenses in this range." not in html


# ------------------------------------------------------------- filter bar

def test_profile_filter_bar_elements_present(auth_client):
    html = _page(auth_client)
    assert 'type="date"' in html
    assert 'name="date_from"' in html
    assert 'name="date_to"' in html
    assert "Apply" in html
    assert "Clear" in html
    assert 'method="get"' in html.lower()


def test_profile_filter_inputs_prefilled_with_applied_values(auth_client):
    html = _page(auth_client, "?date_from=2024-01-10&date_to=2024-01-15")
    assert "2024-01-10" in html
    assert "2024-01-15" in html
    assert 'value="2024-01-10"' in html
    assert 'value="2024-01-15"' in html


def test_profile_inputs_empty_when_no_filter(auth_client):
    html = _page(auth_client)
    assert 'value="2024' not in html


def test_profile_clear_link_points_to_unfiltered_profile(auth_client):
    html = _page(auth_client, "?date_from=2024-01-10")
    assert 'href="/profile"' in html
    # following Clear gives the full data set
    assert len(_present(_page(auth_client))) == 5


# ----------------------------------------------------------- validation

def test_profile_date_from_after_date_to_shows_error_and_unfiltered(auth_client):
    html = _page(auth_client, "?date_from=2024-03-01&date_to=2024-01-01")
    assert _has_error(html), "expected an inline error message"
    assert len(_present(html)) == 5, "must fall back to unfiltered data"


@pytest.mark.parametrize("query", [
    "?date_from=garbage",
    "?date_to=garbage",
    "?date_from=2024-13-45",
    "?date_from=01/10/2024",
    "?date_from=2024-02-30",
    "?date_from=%27%3B+DROP+TABLE+expenses%3B--",
])
def test_profile_invalid_date_does_not_crash_and_shows_error(auth_client, query):
    html = _page(auth_client, query)
    assert _has_error(html), f"expected an error message for {query}"
    assert len(_present(html)) == 5, "invalid bound must be ignored (unfiltered)"


def test_profile_invalid_from_valid_to_ignores_only_bad_bound(auth_client):
    html = _page(auth_client, "?date_from=garbage&date_to=2024-01-10")
    assert _has_error(html)
    assert sorted(_present(html)) == ["ZqAlpha", "ZqBravo"], "valid date_to should still apply"


def test_profile_valid_from_invalid_to_ignores_only_bad_bound(auth_client):
    html = _page(auth_client, "?date_from=2024-02-01&date_to=garbage")
    assert _has_error(html)
    assert sorted(_present(html)) == ["ZqDelta", "ZqEcho"], "valid date_from should still apply"


def test_profile_valid_range_shows_no_error(auth_client):
    html = _page(auth_client, "?date_from=2024-01-01&date_to=2024-01-31")
    assert not _has_error(html) or "invalid" not in html.lower()


def test_profile_equal_from_and_to_is_valid_single_day(auth_client):
    html = _page(auth_client, "?date_from=2024-01-10&date_to=2024-01-10")
    assert _present(html) == ["ZqBravo"]


@pytest.mark.parametrize("query", ["?date_from=&date_to=", "?date_from=", "?date_to="])
def test_profile_blank_params_behave_as_unfiltered(auth_client, query):
    html = _page(auth_client, query)
    assert len(_present(html)) == 5


def test_profile_sql_injection_in_params_leaves_data_intact(auth_client):
    _page(auth_client, "?date_from=2024-01-01%27+OR+%271%27%3D%271&date_to=x%27%3B--")
    assert len(_db_snapshot()) == 6


# ------------------------------------------------------- DB side effects

@pytest.mark.parametrize("query", [
    "",
    "?date_from=2024-01-01&date_to=2024-01-31",
    "?date_from=2024-03-01&date_to=2024-01-01",
    "?date_from=garbage",
    "?date_from=2030-01-01",
])
def test_filtering_never_modifies_data(auth_client, query):
    before = _db_snapshot()
    _page(auth_client, query)
    assert _db_snapshot() == before, "filtering must be read-only"


def test_query_helpers_do_not_modify_data(client):
    before = _db_snapshot()
    queries.get_summary_stats(1, date_from="2024-01-01", date_to="2024-01-31")
    queries.get_recent_transactions(1, date_from="2024-01-01", date_to="2024-01-31")
    queries.get_category_breakdown(1, date_from="2024-01-01", date_to="2024-01-31")
    assert _db_snapshot() == before


def test_profile_filter_does_not_leak_other_users_data(auth_client):
    html = _page(auth_client, "?date_from=2024-01-10&date_to=2024-01-10")
    assert "ZqOtherUser" not in html
    assert "5,000" not in html and "5000" not in html
