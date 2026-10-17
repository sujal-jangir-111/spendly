# Spec: Date Filter Profile Page

## Overview
Step 6 adds a date-range filter to the profile page. Today `/profile` always
shows all-time data. This step lets a logged-in user pick a "from" and "to"
date and see the summary stats, transaction history, and category breakdown
restricted to that range. The filter is driven by query-string parameters on
the existing `GET /profile` route, so filtered views are bookmarkable and need
no JavaScript or new tables.

## Depends on
- Step 1: Database setup (`expenses.date` stored as ISO `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Profile page static UI (`profile.html`, `profile.css`)
- Step 5: Profile backend routes (`database/queries.py` helpers and the
  `build_profile_*` functions in `app.py`)

## Routes
No new routes. `GET /profile` is modified to accept optional query params:
- `date_from` — `YYYY-MM-DD`, inclusive lower bound
- `date_to` — `YYYY-MM-DD`, inclusive upper bound

Access level: logged-in (unchanged; unauthenticated users redirect to `/login`).

## Database changes
No database changes. `expenses.date` is already an ISO text column, so
`date >= ?` / `date <= ?` comparisons work lexically. No index is required at
this scale.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter bar (a `GET` form pointing at `url_for('profile')`) above the
    stats grid with two `<input type="date">` fields (`date_from`, `date_to`),
    an "Apply" submit button, and a "Clear" link to `url_for('profile')`.
  - Pre-fill the inputs with the currently applied values.
  - Show an inline error message when the filter input is invalid.
  - Change the empty-state text of the transaction table to
    "No expenses in this range." when a filter is active
    (keep "No expenses yet." otherwise).

## Files to change
- `database/queries.py` — add optional `date_from=None, date_to=None`
  keyword params to `get_recent_transactions`, `get_summary_stats`, and
  `get_category_breakdown`
- `app.py` — parse and validate the query params in `profile()`, pass them to
  the `build_profile_*` functions, and pass the filter values and any error to
  the template
- `templates/profile.html` — filter bar, error message, empty-state text
- `static/css/profile.css` — styles for the filter bar

## Files to create
- `tests/test_date_filter.py` — tests for the filtered queries and the
  `/profile` route with filters

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — build the `WHERE` clause from fixed fragments
  (`AND date >= ?`, `AND date <= ?`) and pass values as parameters; never
  format user input into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹
- Validate `date_from` and `date_to` with `datetime.strptime(value, "%Y-%m-%d")`.
  An invalid value must not raise: ignore that bound, render the page
  unfiltered for it, and show an error message
- If both bounds are valid and `date_from > date_to`, show an error and fall
  back to the unfiltered view
- Both bounds are optional and independent (only-from and only-to are valid)
- Omitting both params must give exactly the Step 5 behaviour
- The filter applies to all three sections (stats, transactions, categories)
  consistently
- The transaction list keeps its existing limit of 10 rows within the range
- `pct` values must still sum to 100 for the filtered set, and an empty range
  must return zeros / empty lists rather than raising
- Query helpers keep calling `get_db()` internally and closing the connection
  before returning
- Only edit the helpers and `build_profile_*` sections necessary for this
  feature; keep existing function names and route URLs

## Definition of done
- [ ] `/profile` with no query params looks and behaves exactly as before
- [ ] The filter bar shows two date inputs, an Apply button, and a Clear link
- [ ] Submitting a valid range reloads `/profile?date_from=...&date_to=...`
      and the inputs keep the chosen values
- [ ] Total spent, transaction count, and top category reflect only expenses
      within the range (inclusive of both end dates)
- [ ] The transaction table and category breakdown show only in-range
      expenses; category percentages sum to 100
- [ ] A range with no expenses shows ₹0.00, 0 transactions, "—" top category,
      an empty breakdown, and "No expenses in this range."
- [ ] Only `date_from` or only `date_to` filters correctly
- [ ] `date_from` later than `date_to` shows an error and the unfiltered data
- [ ] `?date_from=garbage` does not crash and shows an error message
- [ ] Clear returns to the unfiltered view
- [ ] Visiting `/profile?date_from=...` while logged out redirects to `/login`
- [ ] Tests in `tests/test_date_filter.py` pass with `pytest`
