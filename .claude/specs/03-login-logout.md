# Spec: Login and Logout

## Overview
Make sign-in and sign-out work. Today `GET /login` only renders `login.html`. The form already POSTs `email` and `password` to `/login`, but the route rejects POST, and `/logout` is a placeholder string. This step checks the submitted credentials against the `users` table with werkzeug's `check_password_hash`, stores the user's id and name in Flask's signed `session` cookie on success, and clears the session on logout. The navbar shows different links to logged-in and logged-out users. This step builds on registration (Step 2) and is required by every logged-in page that follows: profile (Step 4) and expense add/edit/delete (Steps 7–9).

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table, seeded `demo@spendly.com` / `demo123`).
- Step 2 — Registration (users exist with werkzeug password hashes; `app.secret_key` is already set).

## Routes
- `GET /login` — render the sign-in form (existing behaviour); if already logged in, redirect to `/profile` — public
- `POST /login` — validate credentials; on success set the session and redirect to `/profile`; on failure re-render `login.html` with an `error` — public
- `GET /logout` — clear the session and redirect to `/` (replaces the placeholder) — public (safe to call when logged out)

Keep the endpoint names `login` and `logout` and their URLs, because `base.html` and other templates link to them with `url_for(...)`. `login()` gains `methods=["GET", "POST"]`.

## Database changes
No database changes. `users` already has `id`, `name`, `email` (UNIQUE, stored lowercase by Step 2) and `password_hash`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — repopulate the email input with the previously submitted value (`value="{{ email or '' }}"`) after a failed attempt; never repopulate the password. Change `action="/login"` to `action="{{ url_for('login') }}"`.
  - `templates/base.html` — make the navbar depend on the session:
    - Logged in (`session.get('user_id')`): show the user's name linking to `url_for('profile')` and a "Log out" link to `url_for('logout')`.
    - Logged out: keep the existing "Sign in" and "Get started" links.

## Files to change
- `app.py` — import `session` from Flask and `check_password_hash` from `werkzeug.security`; implement `POST /login`, the logged-in redirect on `GET /login`, and the real `logout()`.
- `templates/login.html` — see Templates above.
- `templates/base.html` — see Templates above.

## Files to create
- None

## New dependencies
No new dependencies. Flask's built-in `session` and `werkzeug.security` are already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only; never build SQL with f-strings, `%` or `.format()`
- Passwords hashed with werkzeug; verify with `check_password_hash` and never compare plain text
- Use CSS variables and never hardcode hex values. Reuse the existing `.auth-error`, `.form-input`, `.nav-links` and `.nav-cta` styles.
- All templates extend `base.html`
- Use `get_db()` from `database/db.py` and always close the connection (`try/finally` or a `with` block)
- Strip and lowercase `email` before the lookup, the same way registration does
- If either field is blank, show the error "Email and password are required."
- If the email is unknown or the password is wrong, show the same generic message for both: "Invalid email or password." Never reveal which part was wrong.
- On success, call `session.clear()` first and then set `session["user_id"]` and `session["user_name"]`. Store nothing else, and never the password or its hash.
- On failure, re-render `login.html` with `error` and `email` and do not redirect
- On success, `redirect(url_for('profile'))`. Profile is still a Step 4 placeholder, which is expected.
- `logout()` calls `session.clear()` and then `redirect(url_for('landing'))`
- Do not add a `login_required` decorator or protect other routes yet; that belongs to the steps that need it
- Keep all other routes and placeholders unchanged

## Definition of done
- [ ] `GET /login` renders the form with no error when logged out
- [ ] Logging in as `demo@spendly.com` / `demo123` redirects to `/profile`
- [ ] Logging in with an email in different casing or with surrounding spaces (e.g. `  Demo@Spendly.com `) also succeeds
- [ ] A user created through `/register` can then log in with their credentials
- [ ] A wrong password shows "Invalid email or password." and the email field keeps its value while the password field is empty
- [ ] An unregistered email shows the same "Invalid email or password." message
- [ ] Blank fields submitted via curl show "Email and password are required."
- [ ] After login, the navbar shows the user's name and "Log out" instead of "Sign in" and "Get started", on every page
- [ ] Visiting `/login` while logged in redirects to `/profile`
- [ ] Clicking "Log out" redirects to `/`, and the navbar shows "Sign in" and "Get started" again
- [ ] Visiting `/logout` while already logged out redirects to `/` without an error
- [ ] The session cookie contains no password or hash (only `user_id` and `user_name`)
- [ ] App starts with `python app.py` without errors, and `/`, `/register`, `/terms` and `/privacy` still load
