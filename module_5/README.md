Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 5 — Software Assurance + Secure SQL (SQLi Defense) Assignment
Due Date: 2/23/2026

SSH Repo URL: git@github.com:nziran/jhu_software_concepts.git

---
Module 5 Overview

Module 5 focuses on software assurance and secure deployment practices applied to a 
Flask and PostgreSQL web application. The goal of this module is not to add new features, 
but to harden an existing system against common security risks while ensuring the project 
can be reliably installed, tested, and audited in any environment.

This assignment provides hands-on experience with secure coding workflows, including 
static analysis, dependency inspection, environment isolation, and least-privilege 
database access. Particular emphasis is placed on eliminating SQL injection risks, 
enforcing safe database access patterns, and producing a reproducible, security-checked 
codebase suitable for real-world deployment.

Starting from the Module 4 application, the project was refactored to use parameterized 
SQL via psycopg, removing all string-built queries and enforcing explicit LIMIT clauses 
on database access. Database credentials are externalized using environment variables, 
and the application is configured to run with a least-privilege PostgreSQL user to 
minimize the blast radius in the event of a compromise.

In addition to code hardening, the module introduces software supply-chain practices. 
Static analysis is enforced using Pylint with a perfect lint score, dependencies are 
audited and visualized using pydeps and Graphviz, and the project is packaged with 
setup.py to ensure consistent imports and install behavior across environments. 
The application is verified to run in a clean virtual environment using both pip and uv,
demonstrating full reproducibility.

By the end of Module 5, the application passes all tests with 100% coverage, installs 
cleanly in a fresh environment, and includes tooling and documentation that reflect 
modern software assurance standards. The result is a secure, reproducible Flask 
application that demonstrates defensive programming, dependency awareness, and 
production-ready engineering discipline.

---

Environment Requirements

• Python 3.12 or newer
• PostgreSQL 15 or newer
• pip
• virtualenv (or venv module)
• uv (optional, for reproducible installs)

⸻

Project Structure

module_5/
├── src/
│   ├── app.py                # Flask application
│   ├── db.py                 # Secure database connection logic
│   ├── load_data.py          # Initial data loader
│   ├── load_update.py        # Incremental update loader
│   ├── query_data.py         # Analysis queries
│   └── clean_update.py       # Data cleaning logic
│
├── tests/                    # Pytest test suite (100% coverage)
│
├── docs/                     # Sphinx documentation source
│
├── applicant_data_update.json
├── cleaned_applicant_data_update.json
├── llm_extend_applicant_data.json
│
├── dependency.svg            # Python dependency graph (pydeps)
├── requirements.txt          # Runtime + tooling dependencies
├── setup.py                  # Installable package definition
├── pytest.ini                # Pytest configuration
├── README.md                 # Project documentation

Environment Variables

Database configuration is read from environment variables.

Required variables:
	•	DB_HOST
	•	DB_PORT
	•	DB_NAME
	•	DB_USER
	•	DB_PASSWORD

	DATABASE_URL is supported for compatibility, but the application
	is intentionally designed around discrete environment variables 
	to satisfy Module 5 requirements.

⸻

Setup Instructions (Fresh Environment, No Password)
	
	1.	Start PostgreSQL

			psql -U postgres
			CREATE DATABASE gradcafe;
			\q

	2.	Create a least-privilege user (no password)

			psql -U postgres -d gradcafe

			CREATE ROLE app_user LOGIN;
			GRANT CONNECT ON DATABASE gradcafe TO app_user;
			GRANT USAGE ON SCHEMA public TO app_user;
			GRANT SELECT, INSERT ON TABLE public.applicants TO app_user;
			GRANT USAGE ON SEQUENCE public.applicants_p_id_seq TO app_user;

			\q

	3.	Set required environment variables

			export DB_HOST=localhost
			export DB_PORT=5432
			export DB_NAME=gradcafe
			export DB_USER=app_user
			export DB_PASSWORD=””  # empty, since no password

			Alternatively, as mentioned above, you can provide a single DATABASE_URL:

			export DATABASE_URL=“postgresql://app_user@localhost:5432/gradcafe”

	4.	Install dependencies and run the app

			python -m venv .venv
			source .venv/bin/activate
			pip install -r requirements.txt
			pip install -e .
			python src/app.py

	5. 	Verify
	
			•	App runs at http://127.0.0.1:5050
			•	Buttons (Pull Data, Update Analysis) work

	6.  Run pytest
			
			pytest 

			All tests should pass with 100% coverage.

⸻

Pylint Usage

Pylint was run only against the application source code in 
the src/ directory, as required. Test files and the virtual 
environment were intentionally excluded.

Command used:

    pylint src

This command enforces static analysis on all application 
modules (Flask app, database logic, and query code) while 
avoiding false positives from test scaffolding or third-party packages.

---

Dependency Graph

The file dependency.svg shows module-level dependencies generated using pydeps and Graphviz.

Command used: 

	pydeps src/app.py --noshow -T svg -o dependency.svg

⸻

Security Notes

	•	Uses a least-privilege PostgreSQL user
	•	No hard-coded credentials
	•	Parameterized SQL throughout
	•	No dynamic SQL from user input
	•	Database schema creation is intentionally separated 
	    from application runtime execution

⸻

Why Packaging Matters

This project includes a setup.py so it can be installed as a package.

Benefits:
	•	Imports behave consistently across local runs, tests, and CI
	•	Supports editable installs (pip install -e .)
	•	Eliminates path-based “works on my machine” issues
	•	Enables tools like uv to sync environments reliably

---

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

## Deliverables Checklist

✔ **Secure SQL refactor**
- All SQL uses psycopg parameterization (no string-built SQL)
- Statement construction separated from execution
- Explicit LIMIT enforced on all queries

✔ **Static analysis**
- Pylint run on `src/`
- Final score: **10.00 / 10**
- Evidence: `pylint_10of10.png`

✔ **Testing**
- Pytest suite passes with **100% coverage**
- Database schema initialized safely for CI; application runtime uses a 
  least-privilege user
- Tests do not rely on live scraping

✔ **Database hardening**
- No hard-coded credentials
- Configuration via environment variables
- Application runs with a least-privilege PostgreSQL user


✔ **Dependency analysis**
- Dependency graph generated via pydeps + Graphviz
- File: `dependency.svg`

✔ **Snyk Security scanning**
- Dependency scan results: `snyk-analysis.png`
- (Extra credit) SAST results: `snyk-code-test.png`

✔ **Packaging & reproducibility**
- `setup.py` included for installable package
- Fresh install verified via:
  - `pip`
  - `uv`
- Editable installs supported (`pip install -e .`)

✔ **CI enforcement**
- GitHub Actions workflow enforces:
  - Pylint (fail-under=10)
  - Pytest + coverage
  - Dependency graph generation
  - Snyk dependency scan
  - Screenshot of successful CI run included
  - File: `actions_success_module_5.png`

---

## ✅ PDF Deliverable — Detailed Security & Assurance Report

**✔ Included with submission:** `MODULE_5.pdf`

This PDF serves as the **written deliverable** for Module 5 and provides
the full narrative explanations required by the assignment rubric. It expands on the
checklist items above with technical detail, justification, and screenshots.

---

### 🔹 Installation & Reproducibility
- Fresh install instructions using **pip + virtual environments**
- Deterministic installation using **uv**
- Editable installs via `pip install -e .`
- Verification steps for graders running in a clean environment

---

### 🔹 SQL Injection Defenses
- Confirmation that **no runtime user input** influences SQL execution
- Elimination of all string-built SQL (no f-strings, concatenation, or `.format`)
- Clear separation of SQL statements from execution
- Explicit LIMIT enforcement where semantically meaningful
- Explanation of why aggregate queries correctly omit LIMIT

---

### 🔹 Least-Privilege Database Configuration
- Rationale for a dedicated `app_user`
- Exact privileges granted and justification for each
- Confirmation that the application user:
  - is **not a superuser**
  - does **not** own tables
  - cannot modify schema
- SQL snippets used to configure permissions

---

### 🔹 Dependency Graph Analysis
- Explanation of `dependency.svg`
- Justification of `app.py` as the top-level consumer
- Description of module layering and absence of cyclic dependencies

---

### 🔹 Packaging Rationale (`setup.py`)
- Why packaging was required for this project
- How `setup.py` ensures consistent imports across:
  - local runs
  - automated tests
  - CI and grading environments
- Benefits for reproducibility and long-term maintainability

---

### 🔹 Security Scanning (Snyk)
- Dependency scan results (`snyk-analysis.png`)
- Static application security testing results (`snyk-code-test.png`)
- Discussion of findings and justification for:
  - zero high-severity issues
  - development-context medium findings

The PDF deliverable is intended to be read **in conjunction with this README** and should be used as the primary reference for design decisions, security posture, and compliance with all Module 5 requirements.

---

Author
Navid Ziran
2026