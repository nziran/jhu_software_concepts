"""
Tests CLI execution of src.query_data (__main__ guard).
"""

import runpy
import pytest


@pytest.mark.analysis
def test_query_data_main_runs():
    runpy.run_module("src.query_data", run_name="__main__")
