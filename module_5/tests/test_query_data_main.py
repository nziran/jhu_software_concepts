import runpy
import pytest

@pytest.mark.analysis
def test_query_data_main_runs():
    # Executes src/query_data.py as if run from CLI: python -m src.query_data
    runpy.run_module("src.query_data", run_name="__main__")