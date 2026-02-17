Operational Notes
=================

Busy-State Policy
-----------------

The application prevents concurrent ETL pipeline runs to avoid database
corruption and duplicate writes.

When a pull operation is running:

• Additional POST /pull-data requests return HTTP 409 with {"busy": true}
• POST /update-analysis returns HTTP 409 with {“busy”: true} until the pull completes

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

::

  export DATABASE_URL="postgresql://<user>@localhost:5432/gradcafe"

If the app runs but connects to the wrong database:

•	Re-export DATABASE_URL (shown above)
•	Restart Flask in the same terminal

Syntax setup errors
~~~~~~~~~~~~~~~~~~~

During Setup, when copying commands from README.txt, 
some systems automatically replace straight quotes with curly quotes.

This causes errors such as:

•	invalid character
•	no matches found
•	command not found

Fix:

•	Delete the pasted command
•	Retype it manually using plain ASCII quotes ( ' and " )
• If using MacOS, ensure System Settings-->Keyboard-->Text Input-->Input Sources (Edit..)-->Use smart quotes and dashes is OFF


Busy-state stuck
~~~~~~~~~~~~~~~~

If the UI appears locked:

• Check update_job.log for errors
• Restart the Flask server

The job_running flag resets automatically after failures.

Environment variable not set
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If scraping completes but database row counts do not change:

Check row count before and after pull:

::

  psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM applicants;"

If the count does not increase:

• Verify cleaned_applicant_data_update.json was created
• Run clean_update.py manually to confirm output
• Ensure DATABASE_URL was exported before starting Flask:

::

  export DATABASE_URL="postgresql://<user>@localhost:5432/gradcafe"

CI failures
~~~~~~~~~~~

If GitHub Actions fails:

• Verify PostgreSQL service configuration
• Confirm pytest markers and coverage settings
• Ensure all tests pass locally

Run locally:

::
  
  pytest -m "web or buttons or analysis or db or integration"


Missing dependencies
~~~~~~~~~~~~~~~~~~~~

If imports fail:

::

  pip install -r requirements.txt


Documentation build issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

Rebuild Sphinx docs:

::

  cd docs
  make clean
  make html

Open:

docs/build/html/index.html