Overview & Setup
================

Project Overview
----------------

GradCafe is a Flask-based analytics application that ingests applicant data,
stores it in PostgreSQL, and renders analysis results through a web interface.

The system supports:

- Data scraping and normalization
- Database loading and updates
- Analysis queries rendered in a web UI
- Automated testing and CI validation

Environment Requirements
------------------------

This application connects to PostgreSQL using the DATABASE_URL environment variable.

Required:

   DATABASE_URL=postgresql://<user>@localhost:5432/gradcafe

Notes:
	•	Local PostgreSQL authentication uses OS-based trust (no password required).
	•	This project does not use PGDATABASE, PGUSER, or other fallback variables.
	•	If DATABASE_URL is not set, the application will fail to connect.

Running the Application
-----------------------

From the module_4 directory with the DATABASE_URL set:

::

   python -m src.app

Then open your browser to:

::

   http://localhost:5050/analysis

Running Tests
-------------

Run the full marked test suite:

::

   pytest -m "web or buttons or analysis or db or integration"

Coverage enforcement requires 100% test coverage.