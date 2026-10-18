# Spec: Add Expense

## Overview
Step 7 replaces the `/expenses/add` placeholder with a working form that lets a
logged-in user record a new expense (amount, category, date, optional
description). Until now the only expenses come from `seed_db()`; this is the
first feature that writes user data to the `expenses` table. After a successful
save the user lands on `/profile`, where the new expense appears in the
transaction history, stats, and category breakdown built in Steps 5 and 6.

## Depends on
- Step 1: Database setup (`expenses` table, `CATEGORIES` list in `database/db.py`)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4/5: Profile page and backend (where the new expense is displayed)

## Routes
- `GET /expenses/add` — render the empty add-expense form — logged-in
- `POST /expenses/add` — validate the form and insert the expense; on success
  redirect to `/profile`, on error re-render the form with the message and
  the submitted values — logged-in

Unauthenticated users on either method redirect to `/login`. The existing
route name `add_expense` and URL are kept.

## Database changes
No database changes. The existing `expenses` table
(`user_id, amount, category, date, description`) already fits. The new row's
`user_id` always comes from `session["user_id"]`, never from the form.

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`; a `POST` form
  to `url_for('add_expense')` with:
  - `amount` — `<input type="number" step="0.01" min="0.01" required>`
  - `category` — `<select>` populated from `CATEGORIES`
  - `date` — `<input type="date" required>`, defaulting to today
  - `description` — optional text input
  - Submit button and a "Cancel" link to `url_for('profile')`
  - Inline error message block; re-fills the fields after a failed submit
- **Modify:** `templates/profile.html` — add an "Add expense" link/button to
  `url_for('add_expense')` (and to `templates/base.html` navbar only if a
  logged-in nav already exists there)

## Files to change
- `app.py` — implement `add_expense()` for GET and POST; import `CATEGORIES`
  from `database.db`
- `templates/profile.html` — "Add expense" entry point
- `static/css/style.css` or a new page stylesheet — form styles (see below)

## Files to create
- `templates/add_expense.html`
- `static/css/add_expense.css` — form styles, loaded via the `head` block
- `tests/test_add_expense.py` — tests for the route

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never format user input into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹
- Server-side validation is required even though the HTML has client checks:
  - `amount` must parse as a number, be finite, and be greater than 0
    (reject `nan`, `inf`, negatives, zero, non-numeric); round to 2 decimals
  - `category` must be one of `CATEGORIES`
  - `date` must be a valid `YYYY-MM-DD` (reuse `_parse_date`) and not in
    the future
  - `description` is optional, stripped, and capped at 200 characters
- Invalid input must never raise a 500 — re-render with an error message
  and the user's entered values preserved
- Close the DB connection in a `finally` block
- Follow the post-redirect-get pattern on success (`redirect(url_for("profile"))`)
- Keep existing route names and URLs; do not touch the edit/delete placeholders

## Definition of done
- [ ] Visiting `/expenses/add` logged out redirects to `/login`
- [ ] Logged in, `/expenses/add` shows the form with amount, category (all 7
      categories), date (defaulting to today), description, Submit, Cancel
- [ ] Submitting a valid expense redirects to `/profile` and the expense
      appears at the top of the transaction list with the ₹ amount
- [ ] Profile total spent, transaction count, and category breakdown update
      to include the new expense
- [ ] The row is saved under the logged-in user's id and visible only to them
- [ ] Empty amount, zero, negative, `abc`, and `nan` amounts each show an
      error and save nothing
- [ ] An invalid category (tampered POST) shows an error and saves nothing
- [ ] An invalid or future date shows an error and saves nothing
- [ ] After an error the form keeps the user's entered values
- [ ] A blank description is accepted; one over 200 chars shows an error
- [ ] The profile page has a working "Add expense" link to the form
- [ ] Tests in `tests/test_add_expense.py` pass with `pytest`
