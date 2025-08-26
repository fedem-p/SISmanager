"""Pytest configuration and shared fixtures for SISmanager tests."""

import os
import tempfile
import shutil
from typing import Generator
import pandas as pd
import pytest


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_directory = tempfile.mkdtemp()
    yield temp_directory
    if os.path.exists(temp_directory):
        shutil.rmtree(temp_directory)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Sample test data for testing."""
    return pd.DataFrame(
        {
            "orderCode": ["ORDER001", "ORDER002", "ORDER003"],
            "idOrderPos": [1, 2, 3],
            "descrizioneMateriale": ["Material A", "Material B", "Material C"],
            "codiceMateriale": ["MAT001", "MAT002", "MAT003"],
            "quantity": [10, 5, 15],
        }
    )


@pytest.fixture
def duplicate_data() -> pd.DataFrame:
    """Sample test data with duplicates for testing."""
    return pd.DataFrame(
        {
            "orderCode": ["ORDER001", "ORDER001", "ORDER002"],
            "idOrderPos": [1, 1, 2],
            "descrizioneMateriale": ["Material A", "Material A", "Material B"],
            "codiceMateriale": ["MAT001", "MAT001", "MAT002"],
            "quantity": [10, 10, 5],
        }
    )


@pytest.fixture
def sample_xlsx_data() -> pd.DataFrame:
    """Sample data for XLSX testing."""
    return pd.DataFrame(
        {
            "idOrderPos": [1, 2, 3],
            "descrizioneMateriale": ["Material A", "Material B", "Material C"],
            "codiceMateriale": ["MAT001", "MAT002", "MAT003"],
            "quantity": [10, 5, 15],
        }
    )


@pytest.fixture
def backup_test_data() -> str:
    """Test data content for backup testing."""
    return "orderCode,quantity\nORDER001,10\nORDER002,5\n"
