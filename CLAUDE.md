# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly is a Flask + SQLite expense tracker (currency: rupees). It is a step-by-step learning project: many routes and modules are deliberately stubbed with "coming in Step N" placeholders that are meant to be implemented incrementally. Keep the existing route names and URLs when filling them in, since templates link to them via `url_for(...)`.

## Commands

The virtualenv lives one directory up (`../venv`, Windows layout), not inside the repo.

```bash
# Activate venv (PowerShell)
..\venv\Scripts\Activate.ps1
# Activate venv (Git Bash)
source ../venv/Scripts/activate

pip install -r requirements.txt

# Run the dev server (debug mode, http://localhost:5001)
python app.py

# Tests (pytest + pytest-flask; no tests exist yet)
pytest
pytest path/to/test_file.py::test_name   # single test
```

## Architecture

- `app.py` — the single Flask app object and all routes. No blueprints or app factory. Public pages (`/`, `/register`, `/login`, `/terms`, `/privacy`) render templates; `/logout`, `/profile`, and `/expenses/add|<id>/edit|<id>/delete` are placeholders returning strings.
- `database/db.py` — currently empty; it is intended to provide:
  - `get_db()`: returns a SQLite connection with `row_factory` set and foreign keys enabled
  - `init_db()`: creates tables with `CREATE TABLE IF NOT EXISTS`
  - `seed_db()`: inserts sample dev data

  The DB file `expense_tracker.db` is gitignored.
- `templates/` — Jinja templates that all extend `base.html`, which provides the navbar/footer and the `title`, `head`, `content`, and `scripts` blocks. Page-specific CSS goes in the `head` block (for example, `landing.html` loads `landing.css`). `login.html` and `register.html` already contain forms that `POST` to `/login` and `/register`, but those routes currently accept only GET.
- `static/css/style.css` holds the global styles, `static/css/landing.css` styles the landing page, and `static/js/main.js` is an empty placeholder.
