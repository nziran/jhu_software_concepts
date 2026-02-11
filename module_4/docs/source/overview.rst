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

The application connects to PostgreSQL using environment variables.

Preferred (CI / portable):

::

   DATABASE_URL=postgresql://user:password@host:port/database

Fallback variables (local development):

::

   PGDATABASE=gradcafe
   PGUSER=ziran
   PGPASSWORD=your_password
   PGHOST=localhost
   PGPORT=5432

Running the Application
-----------------------

From the module_4 directory:

::

   python -m src.app

Then open your browser to:

::

   http://localhost:5000/analysis

Running Tests
-------------

Run the full marked test suite:

::

   pytest -m "web or buttons or analysis or db or integration"

Coverage enforcement requires 100% test coverage.