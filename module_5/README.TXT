Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 4 — Testing and Documentation Experimentation Assignment
Due Date: 2/15/2026

SSH Repo URL: git@github.com:nziran/jhu_software_concepts.git

---

Overview

This project implements a GradCafe analysis dashboard using a Flask web
application backed by a PostgreSQL database and an ETL pipeline.

It includes:

• Flask web layer for analysis rendering and button-driven workflows
• ETL pipeline for scraping, cleaning, and loading data
• PostgreSQL persistence layer
• Full pytest test suite with markers and CI
• Sphinx documentation with API reference and testing guide

The application supports pulling new data, updating analysis, and rendering
formatted analysis cards.

---

Environment Requirements

• Python 3.12+
• PostgreSQL 15+
• pip
• virtualenv

Environment variable required:

    DATABASE_URL — PostgreSQL connection string

Example:

    postgresql://username@localhost:5432/gradcafe

---

Setup Instructions

1. Create and activate virtual environment in the module_4 directory

    python3 -m venv .venv
    source .venv/bin/activate

2. Install dependencies

    * All commands below must be run from the module_4 directory with the virtual environment activated.

    pip install -r requirements.txt

3.	Configure database

    This application requires a PostgreSQL database connection.

    Step A — Ensure PostgreSQL is running

        Run:

        pg_isready

        You should see:

        accepting connections

    Step B — Create user and database

        Run:

        createuser <your_username>
        createdb -O <your_username> gradcafe

        * Replace <your_username> with your local PostgreSQL username (case-sensitive)

        * if user or gradcafe already exists, user may see ERROR:  user (or gradcafe) already exists

    Step C — Set environment variable

        Run:

        export DATABASE_URL="postgresql://<your_username>@localhost:5432/gradcafe"

        Use the same username you created in Step B

    Step D — Verify database connection

        Run:

        python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL']).close(); print('DB connect OK')"

        * Note: If you copy-paste this command and get a syntax error, retype it manually — some editors auto-convert 
        quotes to curly quotes, which Python does not accept.
    
        * Note: If using MacOS, ensure System Settings-->Keyboard-->Text Input-->Input Sources (Edit..)-->Use smart quotes and dashes is OFF

        If successful, you should see:

        DB connect OK

        This confirms PostgreSQL is reachable and credentials are valid.

    Step E - 

⸻

            Option A — Fresh database

            If the database gradcafe is new (fresh), then continue to Step 3F to load data into it.

⸻

            Option B — Database already exists

            If gradcafe exists and is already populated, user can 
            check whether data already exists:

                psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM applicants;"

            If the count is non-zero, skip Step 3F since data has already been loaded into it and 
            user can go directly to Step 4 (Run the application).

            If gradcafe already exists and was created by a different user, you may see:

                permission denied for table applicants

            Fix this by granting permissions once (run as DB owner or superuser):

            psql -d gradcafe -c "GRANT CONNECT ON DATABASE gradcafe TO <your_username>;
            GRANT USAGE, CREATE ON SCHEMA public TO <your_username>;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO <your_username>;
            GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO <your_username>;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <your_username>;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO <your_username>;"

            After this, proceed normally.

⸻

Step F — Populate the database (create applicants table)

If the database is empty, run:

python src/load_data.py

The loader will:

• Create the applicants table if missing
• Insert cleaned applicant records
• Safely skip duplicates

Verify success:

    psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM applicants;"

A non-zero count confirms successful population.


Environment Variable Reminder (Important)

    Environment variables do not persist when you open a new terminal session. If you close Terminal and reopen it, 
    you must re-export the database connection string.  The db connection string tells the app which database to use.

    Verify the variable is set:

        echo $DATABASE_URL

    If nothing prints, re-export it:

        export DATABASE_URL="postgresql://<your_username>@localhost:5432/gradcafe"

    You can confirm the database connection with:

        psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM applicants;"

    If successful, PostgreSQL will return a row count. This confirms the database is reachable and correctly configured.


4. Run the application

    python -m src.app

    Open browser:

    http://127.0.0.1:5050/analysis

---

Running tests (marker policy check):

    pytest -m "web or buttons or analysis or db or integration"

    Runs the full marked suite and verifies that all tests are properly marked according to assignment policy.

---

Running tests with coverage enforcement:

    pytest

    Runs the entire test suite with pytest-cov enforcing 100% coverage as configured in pytest.ini.

Test Coverage Summary

The test suite validates all required behaviors for the GradCafe application.

Representative tests include:

• Flask app & rendering — test_flask_page.py
Verifies app creation, route availability, and correct rendering of the analysis page.

• Buttons & busy-state behavior — test_buttons.py
Ensures pull/update endpoints respond correctly and enforce concurrency gating.

• Analysis formatting — test_analysis_format.py
Confirms labels and percentage formatting rules.

• Database writes — test_db_insert.py
Validates inserts, idempotency, and query integrity.

• Integration workflows — test_integration_end_to_end.py
Simulates pull → update → render pipeline using injected test data.

Additional unit tests provide full branch coverage of scraping, loading, query logic, and helper functions.


---

Architecture Summary

Web Layer (Flask)
Handles routes, rendering, busy-state gating, and UI selectors.

ETL Layer
Scrapes external data, cleans/normalizes content, and loads database records.

Database Layer (PostgreSQL)
Stores applicant records and supports analysis queries.

Query Layer
Aggregates database results into analysis cards rendered by Flask.

---

Sphinx Documentation

Documentation source:

    module_4/docs/

Build locally:

    cd docs
    make html

Open:

    docs/build/html/index.html

Documentation includes:

• Overview & setup guide
• Architecture explanation
• API autodoc reference
• Testing guide
• Operational Notes (busy-state policy, idempotency, troubleshooting)

Published documentation online:

    https://gradcafe-ziran.readthedocs.io/en/latest/

---

GitHub Actions CI

Automated CI runs pytest with PostgreSQL service container and coverage enforcement.

---

Assignment Deliverables

The repository includes all required Module 4 deliverables:

✔ SSH GitHub repository containing full project source  
✔ README located under module_4  
✔ requirements.txt under module_4  
✔ Fully marked pytest test suite under module_4/tests  
✔ Sphinx documentation project under module_4/docs  
✔ Generated Sphinx HTML documentation under module_4/docs/build  
✔ PostgreSQL integration and ETL pipeline implementation  
✔ 100% coverage proof via coverage_summary.txt  
✔ GitHub Actions CI pipeline configuration (.github/workflows/tests.yml)

Proof Deliverables

• actions_success.png — screenshot showing successful GitHub Actions CI run
• rtd_build_success.png — screenshot confirming ReadTheDocs build completed successfully
• rtd_published_site.png — screenshot showing live published Sphinx documentation

Live Sphinx documentation:

https://gradcafe-ziran.readthedocs.io/en/latest/

Documentation includes Overview, Architecture, API reference, Testing guide, 
and Operational Notes (busy-state policy, idempotency, troubleshooting).
---

Notes

• Tests do not rely on live scraping
• Dependency injection enables deterministic testing
• Busy-state gating prevents concurrent ETL jobs
• Analysis percentages formatted to two decimals

---

Pylint Usage

• Pylint was run on all Python code files in Module 5 using the following command:
        
     python -m pylint src
     

This command ensures that pylint is run inside the venv.  
All files in module 5 were tested, however the src folder was linted first.

Exceptions

clean_update.py:
- _extract_start_term_year: disabled R0911 (too-many-return-statements) — multiple early exits, logical.
- clean_data: disabled R0914 (too-many-locals) — long list of variables needed for schema normalization.

scrape_update.py:
- scrape_data: disabled R0914 (too-many-locals) — function legitimately manages many temporary variables.
- scrape_data: disabled R0912 (too-many-branches) — multiple control branches for error handling and logic.
- scrape_data: disabled R0915 (too-many-statements) — long pipeline, combining scraping, filtering, and futures processing.

load_data.py:
- safe_float: disabled R0801 (duplicate-code) — common small utility also appears in load_update.py.
- _db_params / db_url return: disabled R0801 (duplicate-code) — same pattern appears in query_data.py.

app.py:
	•	analysis_cache / analysis_last_updated: disabled C0103 (invalid-name) — global cache/timestamp variables used by Flask routes; renaming would complicate code unnecessarily.
	•	job_running / job_last_message: disabled C0103 (invalid-name) — global state variables tracking background update; renaming not practical.
	•	run_update_pipeline, analysis, pull_data, update_analysis: disabled W0603 / W0602 (global-statement / global-variable-not-assigned) — globals are intentionally read/modified for background thread and cached state; required for thread-safe UI logic.
	•	run_update_pipeline: disabled W0718 (broad-exception-caught) — catches general exceptions to prevent background thread from crashing the Flask server.
	•	Imports: disabled C0411 (wrong-import-order) — standard library imports intentionally grouped for clarity and readability.


query_data.py:
	•	get_analysis_cards: disabled R1735 (use-dict-literal) — returning dicts for DB connection parameters; literal dict alternative is stylistic, not functionally necessary.
	•	get_analysis_cards: disabled too-many-locals — multiple temporary variables needed to fetch, calculate, and format all analysis card queries; splitting would reduce readability and complicate flow.
	•	get_analysis_cards: disabled duplicate-code — small repeated patterns exist in load_data.py and load_update.py; intentional for consistency.
	•	Final newline missing (C0304) — cosmetic, does not affect runtime.
	•	Long SQL query lines (C0301) — line wrapping would reduce readability for multi-line SQL; left as-is for clarity in queries.

load_update.py:
	•	safe_float / _date_parse functions: disabled R0801 (duplicate-code) — same small utilities appear in load_data.py.
	•	Final newline missing (C0304) — purely cosmetic, no runtime effect.
	•	Catching general exceptions (W0718) — these are utility wrappers around DB insert/commit; specific exception handling is unnecessary because failures are logged and returned upstream.


Author
Navid Ziran
2026