import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

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

    # Hardcoded sample data — real queries are wired up in Step 5.
    name = session.get("user_name", "Demo User")
    user = {
        "name": name,
        "initials": "".join(part[0] for part in name.split()[:2]).upper(),
        "email": "demo@spendly.com",
        "member_since": "January 2026",
    }
    stats = {
        "total_spent": "₹3,899.00",
        "transaction_count": 8,
        "top_category": "Bills",
    }
    transactions = [
        {"date": "22 Oct 2026", "description": "Lunch out", "category": "Food", "tone": "tone-green", "amount": "₹180.00"},
        {"date": "18 Oct 2026", "description": "Gift", "category": "Other", "tone": "tone-rose", "amount": "₹200.00"},
        {"date": "14 Oct 2026", "description": "T-shirt", "category": "Shopping", "tone": "tone-plum", "amount": "₹899.00"},
        {"date": "11 Oct 2026", "description": "Movie tickets", "category": "Entertainment", "tone": "tone-blue", "amount": "₹300.00"},
        {"date": "08 Oct 2026", "description": "Pharmacy", "category": "Health", "tone": "tone-rose", "amount": "₹450.00"},
        {"date": "05 Oct 2026", "description": "Electricity bill", "category": "Bills", "tone": "tone-amber", "amount": "₹1,500.00"},
        {"date": "03 Oct 2026", "description": "Metro card recharge", "category": "Transport", "tone": "tone-blue", "amount": "₹120.00"},
        {"date": "01 Oct 2026", "description": "Groceries", "category": "Food", "tone": "tone-green", "amount": "₹250.00"},
    ]
    categories = [
        {"name": "Bills", "tone": "tone-amber", "amount": "₹1,500.00", "pct": 38},
        {"name": "Shopping", "tone": "tone-plum", "amount": "₹899.00", "pct": 23},
        {"name": "Food", "tone": "tone-green", "amount": "₹430.00", "pct": 11},
        {"name": "Health", "tone": "tone-rose", "amount": "₹450.00", "pct": 12},
        {"name": "Entertainment", "tone": "tone-blue", "amount": "₹300.00", "pct": 8},
        {"name": "Other", "tone": "tone-rose", "amount": "₹200.00", "pct": 5},
        {"name": "Transport", "tone": "tone-blue", "amount": "₹120.00", "pct": 3},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


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
