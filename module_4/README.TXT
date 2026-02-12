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

postgresql://user:password@localhost:5432/gradcafe

---

Setup Instructions

1. Create and activate virtual environment

    python -m venv .venv
    source .venv/bin/activate

2. Install dependencies

    pip install -r requirements.txt

3.	Configure database

    This application requires a PostgreSQL database connection.

    Step A — Ensure PostgreSQL is running

    Run:

    pg_isready

    You should see:

    accepting connections

    Step B — Create database and user (local example)

    Run:

    createuser ziran
    createdb -O ziran gradcafe

    Step C — Set environment variable

    Run:

    export DATABASE_URL=“postgresql://ziran@localhost:5432/gradcafe”

    Step D — Verify database connection

    Run:

    python -c “import os, psycopg; psycopg.connect(os.environ[‘DATABASE_URL’]).close(); print(‘DB connect OK’)”

    If successful, you should see:

    DB connect OK

    This confirms the database is configured correctly.

4. Run the application

    python -m src.app

    Open browser:

    http://127.0.0.1:5000/analysis

---

Running Tests

Run the entire marked suite:

pytest -m "web or buttons or analysis or db or integration"

Generate coverage report:

pytest --cov=src

Tests verify:

• Web endpoints
• Busy gating behavior
• Database writes and idempotency
• Analysis formatting
• End-to-end workflows

All tests are marked per assignment requirements.

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

Published documentation:

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

---

Notes

• Tests do not rely on live scraping
• Dependency injection enables deterministic testing
• Busy-state gating prevents concurrent ETL jobs
• Analysis percentages formatted to two decimals

---

Author
Navid Ziran
2026