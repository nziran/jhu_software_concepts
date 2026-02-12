Operational Notes
=================

Busy-State Policy
-----------------

The application prevents concurrent ETL pipeline runs to avoid database
corruption and duplicate writes.

When a pull operation is running:

• Additional POST /pull-data requests return HTTP 409 with {"busy": true}
• POST /update-analysis is blocked until the pull completes

A global lock and job_running flag enforce this policy. The flag resets
even if a pipeline error occurs, ensuring the UI never becomes permanently
locked.

This behavior is verified by automated tests.


Idempotency Strategy
--------------------

The ETL pipeline is designed so repeated pulls do not create duplicate rows.

Key safeguards include:

• Database uniqueness constraints
• Loader logic that inserts only new records
• Tests verifying repeated pulls preserve row counts

This ensures data integrity even if the same dataset is processed multiple
times.


Uniqueness Rules
----------------

Records are uniquely identified using the schema rules established in
Module 3.

Duplicate survey entries are rejected at insert time, guaranteeing that:

• Pulling identical data twice does not inflate totals
• Overlapping datasets merge safely

These guarantees are validated by database unit tests.


Troubleshooting
---------------

Database connection errors
~~~~~~~~~~~~~~~~~~~~~~~~~~

If the app or tests fail to connect:

• Ensure PostgreSQL is running
• Confirm DATABASE_URL is set correctly

Example:

export DATABASE_URL="postgresql://user@localhost:5432/gradcafe"


Busy-state stuck
~~~~~~~~~~~~~~~~

If the UI appears locked:

• Check update_job.log for errors
• Restart the Flask server

The job_running flag resets automatically after failures.


CI failures
~~~~~~~~~~~

If GitHub Actions fails:

• Verify PostgreSQL service configuration
• Confirm pytest markers and coverage settings
• Ensure all tests pass locally

Run locally:

pytest -m "web or buttons or analysis or db or integration"


Missing dependencies
~~~~~~~~~~~~~~~~~~~~

If imports fail:

pip install -r requirements.txt


Documentation build issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

Rebuild Sphinx docs:

cd docs
make clean
make html

Open:

docs/build/html/index.html