"""Read-only query helpers for the profile page. No Flask imports.

Each helper opens its own connection via get_db() and closes it before returning.
Raw values are returned (ISO dates, float amounts); display formatting happens in app.py.
"""
from datetime import datetime

from database.db import get_db


def _date_clause(date_from, date_to):
    """Return (sql_fragment, params) restricting expenses.date to an inclusive range.
    The fragment is built only from fixed strings; values are passed as parameters."""
    sql, params = "", []
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    return sql, params


# ---- user ---------------------------------------------------------------- #

def get_user_by_id(user_id):
    """Return {"name", "email", "member_since"} ("Month YYYY") or None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


# ---- SECTION 1: transaction history (subagent 1) ------------------------- #

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Return list of {"date" (ISO str), "description", "category", "amount" (float)},
    newest first (date DESC, id DESC). Empty list if none."""
    clause, params = _date_clause(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *params, limit),
        ).fetchall()
        return [
            {
                "date": r["date"],
                "description": r["description"] or "",
                "category": r["category"],
                "amount": float(r["amount"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


# ---- SECTION 2: summary stats (subagent 2) ------------------------------- #

def get_summary_stats(user_id, date_from=None, date_to=None):
    """Return {"total_spent" (float), "transaction_count" (int), "top_category" (str)}.
    top_category is the category with the highest total; no expenses ->
    {"total_spent": 0, "transaction_count": 0, "top_category": "—"}."""
    clause, params = _date_clause(date_from, date_to)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id, *params),
        ).fetchone()
        if not row["cnt"]:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + clause +
            " GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
            (user_id, *params),
        ).fetchone()
        return {
            "total_spent": float(row["total"]),
            "transaction_count": int(row["cnt"]),
            "top_category": top["category"],
        }
    finally:
        conn.close()


# ---- SECTION 3: category breakdown (subagent 3) -------------------------- #

def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Return list of {"name", "amount" (float), "pct" (int)} ordered by amount desc.
    pct values are ints summing to 100 (largest category absorbs rounding remainder).
    Empty list if no expenses."""
    clause, params = _date_clause(date_from, date_to)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id, *params),
        ).fetchall()
    finally:
        db.close()

    grand = sum(r["total"] for r in rows)
    if not rows or grand <= 0:
        return []
    result = [
        {
            "name": r["category"],
            "amount": float(r["total"]),
            "pct": round(r["total"] / grand * 100),
        }
        for r in rows
    ]
    result[0]["pct"] += 100 - sum(c["pct"] for c in result)
    return result
