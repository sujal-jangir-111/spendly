import os
import sqlite3
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


def _is_valid_email(email):
    local, at, domain = email.partition("@")
    return bool(local) and bool(at) and "." in domain.strip(".")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not name or not email or not password:
        error = "All fields are required."
    elif not _is_valid_email(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    else:
        conn = get_db()
        try:
            if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                error = "An account with that email already exists."
            else:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            error = "An account with that email already exists."
        finally:
            conn.close()

    if error:
        return render_template("register.html", error=error, name=name, email=email)
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    user = None
    if not email or not password:
        error = "Email and password are required."
    else:
        conn = get_db()
        try:
            user = conn.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."

    if error:
        return render_template("login.html", error=error, email=email)

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout") 
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  # 
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user_row = get_user_by_id(user_id)
    if user_row is None:
        session.clear()
        return redirect(url_for("login"))

    date_filter = _resolve_date_filter(request.args)
    date_from = date_filter["date_from"] or None
    date_to = date_filter["date_to"] or None

    user = {
        "name": user_row["name"],
        "initials": "".join(part[0] for part in user_row["name"].split()[:2]).upper(),
        "email": user_row["email"],
        "member_since": user_row["member_since"],
    }
    return render_template(
        "profile.html",
        user=user,
        stats=build_profile_stats(user_id, date_from=date_from, date_to=date_to),
        transactions=build_profile_transactions(user_id, date_from=date_from, date_to=date_to),
        categories=build_profile_categories(user_id, date_from=date_from, date_to=date_to),
        date_filter=date_filter,
    )


# ------------------------------------------------------------------ #
# Profile data builders — each section is owned by one subagent.      #
# Do not edit outside your own section.                               #
# ------------------------------------------------------------------ #

CATEGORY_TONES = {
    "Food": "tone-green",
    "Transport": "tone-blue",
    "Bills": "tone-amber",
    "Health": "tone-rose",
    "Entertainment": "tone-blue",
    "Shopping": "tone-plum",
    "Other": "tone-rose",
}
DEFAULT_TONE = "tone-rose"


def _format_inr(amount):
    return f"₹{amount:,.2f}"


def _parse_date(value):
    """Return value normalised to YYYY-MM-DD if it is a valid date, else None."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _resolve_date_filter(args):
    """Validate the date_from / date_to query params.

    Returns {"date_from", "date_to" ("" when unset), "active", "error"}.
    An invalid bound is dropped; a reversed range drops both.
    """
    raw_from = args.get("date_from", "").strip()
    raw_to = args.get("date_to", "").strip()
    date_from = _parse_date(raw_from) if raw_from else None
    date_to = _parse_date(raw_to) if raw_to else None

    error = None
    if (raw_from and date_from is None) or (raw_to and date_to is None):
        error = "Please enter valid dates."
    elif date_from and date_to and date_from > date_to:
        error = "Start date must be on or before end date."
        date_from = date_to = None

    return {
        "date_from": date_from or "",
        "date_to": date_to or "",
        "active": bool(date_from or date_to),
        "error": error,
    }


# ==== SECTION 1: transaction history (subagent 1) ==================== #

def build_profile_transactions(user_id, date_from=None, date_to=None):
    """Template-ready rows: date (DD Mon YYYY), description, category, tone, amount."""
    return [
        {
            "date": datetime.strptime(t["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": t["description"],
            "category": t["category"],
            "tone": CATEGORY_TONES.get(t["category"], DEFAULT_TONE),
            "amount": _format_inr(t["amount"]),
        }
        for t in get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    ]


# ==== SECTION 2: summary stats (subagent 2) ========================== #

def build_profile_stats(user_id, date_from=None, date_to=None):
    """Template-ready dict: total_spent (formatted), transaction_count, top_category."""
    stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    return {
        "total_spent": _format_inr(stats["total_spent"]),
        "transaction_count": int(stats["transaction_count"]),
        "top_category": stats["top_category"],
    }


# ==== SECTION 3: category breakdown (subagent 3) ===================== #

def build_profile_categories(user_id, date_from=None, date_to=None):
    """Template-ready rows: name, tone, amount (formatted), pct."""
    return [
        {
            "name": c["name"],
            "tone": CATEGORY_TONES.get(c["name"], DEFAULT_TONE),
            "amount": _format_inr(c["amount"]),
            "pct": c["pct"],
        }
        for c in get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    ]


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
