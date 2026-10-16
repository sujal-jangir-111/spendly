# Spec: Registration

## Overview
Make the existing registration page functional. Today `GET /register` only renders `register.html`; the form already POSTs `name`, `email` and `password` to `/register`, but the route rejects POST. This step adds server-side handling: validate the input, reject duplicate emails, hash the password with werkzeug, insert the user into the `users` table, and redirect to the login page. It is the first feature built on top of the Step 1 data layer and is the prerequisite for login/logout (Step 3) and every logged-in page after it.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with `UNIQUE` email).

## Routes
- `GET /register` — render the registration form (existing behaviour, unchanged) — public
- `POST /register` — validate input, create the user, redirect to `/login` on success; re-render `register.html` with an `error` message on failure — public

The existing `register` endpoint name and `/register` URL must be kept (`url_for('register')` is used in `base.html` and `login.html`); the route just gains `methods=["GET", "POST"]`.

## Database changes
No database changes. The `users` table in `database/db.py` already has `id`, `name`, `email TEXT NOT NULL UNIQUE`, `password_hash`, and `created_at DEFAULT (datetime('now'))`, which covers everything registration needs.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — repopulate `name` and `email` inputs with the previously submitted values (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`) when the form is re-rendered with an error; add `minlength="8"` to the password input to match the "Min. 8 characters" placeholder. Never repopulate the password.

## Files to change
- `app.py` — import `request`, `redirect`, `url_for` from Flask and `generate_password_hash` from `werkzeug.security`; set `app.secret_key` (read from the `SECRET_KEY` environment variable with a dev fallback) so sessions/flash work in later steps; change `register()` to accept GET and POST and implement the POST logic.
- `templates/register.html` — see Templates above.

## Files to create
- None

## New dependencies
No new dependencies. `flask` and `werkzeug` are already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with f-strings or `%`/`.format()`
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log the plain password
- Use CSS variables — never hardcode hex values (reuse the existing `.auth-error`, `.form-input` styles)
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; always close the connection (use `try/finally` or a `with` block)
- Validation, all done server-side (HTML `required` is not enough):
  - Strip whitespace from `name` and `email`; lowercase `email` before checking/storing
  - All three fields required → error "All fields are required."
  - Email must contain `@` and a `.` after it → error "Please enter a valid email address."
  - Password at least 8 characters → error "Password must be at least 8 characters."
  - Email already registered → error "An account with that email already exists."
- Check for an existing email with a `SELECT` before inserting, and also catch `sqlite3.IntegrityError` on the insert as a fallback for the same error message
- On validation failure re-render `register.html` with `error`, `name`, `email` (HTTP 200 is fine); do not redirect
- On success `redirect(url_for('login'))` (Post/Redirect/Get) — do not log the user in automatically; login is Step 3
- Keep all other routes and placeholder routes unchanged

## Definition of done
- [ ] `GET /register` still renders the form with no error shown
- [ ] Submitting a new name, email and 8+ character password redirects to `/login`
- [ ] The new user appears in the `users` table with a werkzeug hash in `password_hash` (starts with `scrypt:` or `pbkdf2:`), not the plain password
- [ ] The stored email is lowercase and trimmed even if typed as `  Test@Example.COM `
- [ ] Registering again with the same email (any casing) shows "An account with that email already exists." and creates no new row
- [ ] Submitting a password shorter than 8 characters shows "Password must be at least 8 characters." and creates no row
- [ ] Submitting an invalid email (e.g. `abc`) shows "Please enter a valid email address."
- [ ] Submitting blank/whitespace-only fields (bypassing browser validation, e.g. via curl) shows "All fields are required."
- [ ] After an error, the name and email fields keep their submitted values; the password field is empty
- [ ] Registering `demo@spendly.com` (the seeded user) is rejected as a duplicate
- [ ] App starts with `python app.py` without errors and all other pages (`/`, `/login`, `/terms`, `/privacy`) still load
