Architecture
============

High-Level Flow
---------------

The GradCafe application has three main layers:

1. Web layer (Flask): HTTP routes + HTML rendering
2. ETL layer: pull/scrape, clean/normalize, load/update
3. Database layer (PostgreSQL): persistent storage + query engine

Web Layer (Flask)
-----------------

**Module:** ``src/app.py``

Responsibilities:

- Exposes routes such as ``GET /analysis`` and POST endpoints used by the UI
- Renders analysis cards returned by the query layer
- Enforces "busy" gating so long-running jobs don't overlap
- Provides stable selectors used by tests (e.g., ``data-testid``)

ETL Layer
---------

ETL is split into small scripts/modules so tests can inject fakes and avoid live network access.

Typical responsibilities:

- Pull/scrape data (tests must not depend on live internet)
- Clean/normalize the scraped data into a consistent schema
- Load/insert records into PostgreSQL (idempotent behavior enforced via uniqueness)

Database Layer
--------------

**Primary table:** ``applicants``

Responsibilities:

- Stores applicant records with required (non-null) fields per Module-3 schema
- Prevents duplication via uniqueness policy (e.g., unique URL)
- Supports queries used to generate the analysis page

Query/Analysis Layer
--------------------

**Module:** ``src/query_data.py``

Responsibilities:

- Connects to Postgres using ``DATABASE_URL`` environment variable
- Executes SQL queries against ``applicants``
- Returns analysis results as "analysis cards" used by the web layer:

::

   [{"id": "Q1", "question": "...", "answer": "..."}, ...]