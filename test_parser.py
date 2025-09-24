"""
Test Suite for Bank Statement Parsers
-------------------------------------
This script contains a suite of `pytest` tests designed to validate the
correctness and reliability of the AI-generated bank statement parsers.
"""
import pytest
import pandas as pd
from pathlib import Path
import importlib.util

@pytest.fixture(scope="class")
def bank_name():
    """Provides the target bank's identifier for the test session."""
    return "icici"

class TestBankStatementParser:
    """A collection of tests that validate the functionality of a bank statement parser."""

    @pytest.fixture(scope="class")
    def parser_module(self, bank_name):
        """Dynamically loads the AI-generated parser module for testing."""
        parser_path = Path.cwd() / f"custom_parsers/{bank_name}_parser.py"
        if not parser_path.exists():
            pytest.skip(f"Parser not found at {parser_path}. Skipping tests.")
        
        spec = importlib.util.spec_from_file_location(f"{bank_name}_parser", parser_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @pytest.fixture(scope="class")
    def expected_data(self, bank_name):
        """Loads the ground-truth data from the sample CSV file."""
        csv_path = Path.cwd() / f"data/{bank_name}/{bank_name}_sample.csv"
        if not csv_path.exists():
            pytest.fail(f"Critical test file missing: Expected CSV not found at {csv_path}")
        
        df = pd.read_csv(csv_path)
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y').dt.strftime('%d-%m-%Y')
        for col in ['Debit Amt', 'Credit Amt', 'Balance']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    @pytest.fixture(scope="class")
    def pdf_path(self, bank_name):
        """Provides the path to the sample PDF file to be parsed."""
        path = Path.cwd() / f"data/{bank_name}/{bank_name}_sample.pdf"
        if not path.exists():
            pytest.fail(f"Critical test file missing: Sample PDF not found at {path}")
        return str(path)

    # --- Test Cases ---

    def test_parser_contract(self, parser_module, pdf_path, expected_data):
        """Validates the fundamental 'contract' of the parser: its output structure."""
        result = parser_module.parse(pdf_path)
        
        assert isinstance(result, pd.DataFrame), "The parser must return a pandas DataFrame."
        
        expected_cols = ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']
        assert list(result.columns) == expected_cols, (
            f"Column mismatch: Expected {expected_cols}, but the parser produced {list(result.columns)}. "
            "Ensure the parser does not invent extra columns."
        )
        
        assert result.shape == expected_data.shape, f"Shape mismatch: Got {result.shape}, Expected {expected_data.shape}."

    def test_exact_match(self, parser_module, pdf_path, expected_data):
        """Performs a cell-by-cell comparison of the parsed data against the ground-truth data."""
        result = parser_module.parse(pdf_path)
        try:
            pd.testing.assert_frame_equal(result, expected_data, check_dtype=False)
        except AssertionError as e:
            pytest.fail(f"The parsed DataFrame's content does not exactly match the expected CSV.\nDetails: {e}")