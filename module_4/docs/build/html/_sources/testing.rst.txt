Testing Guide
=============

Test markers (required)
-----------------------

All tests in this project are marked with one (or more) of these markers:

- ``web``
- ``buttons``
- ``analysis``
- ``db``
- ``integration``

To run the full suite (the grading command), from ``module_4/``:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"


Quick local runs
----------------

Run everything:

.. code-block:: bash

   pytest

Run only a subset (examples):

.. code-block:: bash

   pytest -m web
   pytest -m db
   pytest -m integration


Stable UI selectors used in tests
---------------------------------

The UI tests rely on stable HTML selectors (``data-testid`` attributes) so tests
do not break when styling changes.

Required selectors:

- Pull button: ``data-testid="pull-data-btn"``
- Update button: ``data-testid="update-analysis-btn"``


Test doubles / dependency injection
-----------------------------------

This project avoids live network calls during tests.

In tests, the ETL pipeline functions (scrape/load/update) are replaced with
fakes/mocks so that:

- tests are deterministic
- no real GradCafe scraping is performed
- database writes can be asserted safely

Busy-state tests verify that when a pull is in progress:

- ``POST /pull-data`` and/or ``POST /update-analysis`` returns ``409`` with
  ``{"busy": true}`` (per route behavior), and no work is performed.


Formatting expectations asserted by tests
-----------------------------------------

The analysis page must:

- render at least one ``Answer:`` label
- render percentages with **two decimals** (example: ``39.28%``)