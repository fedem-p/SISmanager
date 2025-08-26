"""Unit tests for CentralDBRepository."""

import os
from unittest.mock import patch
import pandas as pd
import pytest

from src.central_db_repository import CentralDBRepository


@pytest.fixture
def test_db_path(temp_dir: str) -> str:
    """Create test database path."""
    return os.path.join(temp_dir, "test_central_db.csv")


@pytest.fixture
def repository(test_db_path: str) -> CentralDBRepository:
    """Create CentralDBRepository instance for testing."""
    return CentralDBRepository(test_db_path)


def test_init_default_path():
    """Test repository initialization with default path."""
    repo = CentralDBRepository()
    assert repo.db_path is not None
    assert repo.db_path.endswith("central_db.csv")


def test_init_custom_path():
    """Test repository initialization with custom path."""
    custom_path = "/custom/path/db.csv"
    repo = CentralDBRepository(custom_path)
    assert repo.db_path == custom_path


def test_exists_file_not_exists(repository: CentralDBRepository):
    """Test exists() when file doesn't exist."""
    assert not repository.exists()


def test_exists_file_exists(
    repository: CentralDBRepository, test_db_path: str, sample_data: pd.DataFrame
):
    """Test exists() when file exists."""
    sample_data.to_csv(test_db_path, index=False)
    assert repository.exists()


def test_read_empty_file(repository: CentralDBRepository):
    """Test read() when file doesn't exist."""
    result = repository.read()
    assert result.empty


def test_read_existing_file(
    repository: CentralDBRepository, test_db_path: str, sample_data: pd.DataFrame
):
    """Test read() when file exists."""
    sample_data.to_csv(test_db_path, index=False)
    result = repository.read()
    pd.testing.assert_frame_equal(result, sample_data)


def test_write(
    repository: CentralDBRepository, test_db_path: str, sample_data: pd.DataFrame
):
    """Test write() functionality."""
    repository.write(sample_data)
    assert os.path.exists(test_db_path)

    # Verify written data
    written_data = pd.read_csv(test_db_path)
    pd.testing.assert_frame_equal(written_data, sample_data)


def test_append_to_new_file(
    repository: CentralDBRepository, test_db_path: str, sample_data: pd.DataFrame
):
    """Test append() to a new file (should create with headers)."""
    repository.append(sample_data)
    assert os.path.exists(test_db_path)

    written_data = pd.read_csv(test_db_path)
    pd.testing.assert_frame_equal(written_data, sample_data)


def test_append_to_existing_file(
    repository: CentralDBRepository, sample_data: pd.DataFrame
):
    """Test append() to an existing file."""
    # First write some data
    initial_data = sample_data.iloc[:2]
    repository.write(initial_data)

    # Then append more data
    new_data = sample_data.iloc[2:]
    repository.append(new_data)

    # Verify combined data
    result = repository.read()
    pd.testing.assert_frame_equal(result, sample_data)


def test_deduplicate_empty_dataframe(repository: CentralDBRepository):
    """Test deduplicate() with empty dataframe."""
    result = repository.deduplicate()
    assert result == 0


def test_deduplicate_forceful_mode(
    repository: CentralDBRepository, duplicate_data: pd.DataFrame
):
    """Test deduplicate() in forceful mode."""
    repository.write(duplicate_data)

    result = repository.deduplicate(mode="forceful")
    assert result == 1  # Should remove 1 duplicate

    # Verify duplicates are removed
    final_data = repository.read()
    assert len(final_data) == 2
    assert not final_data.duplicated().any()


@patch("builtins.input", side_effect=["y", "n"])
def test_deduplicate_soft_mode(
    mock_input, repository: CentralDBRepository, duplicate_data: pd.DataFrame
):
    """Test deduplicate() in soft mode with user confirmation."""
    repository.write(duplicate_data)

    result = repository.deduplicate(mode="soft")
    assert (
        result == 1
    )  # Should remove 1 duplicate (user said 'y' to first, 'n' to second)


def test_deduplicate_invalid_mode(
    repository: CentralDBRepository, duplicate_data: pd.DataFrame
):
    """Test deduplicate() with invalid mode."""
    repository.write(duplicate_data)

    result = repository.deduplicate(mode="invalid")
    assert result == 0


def test_export_to_xlsx_empty_dataframe(repository: CentralDBRepository, temp_dir: str):
    """Test export_to_xlsx() with empty dataframe."""
    output_path = os.path.join(temp_dir, "empty_export.xlsx")

    # Should not create file and should not raise exception
    repository.export_to_xlsx(output_path)
    assert not os.path.exists(output_path)


def test_export_to_xlsx_with_data(
    repository: CentralDBRepository, temp_dir: str, sample_data: pd.DataFrame
):
    """Test export_to_xlsx() with data."""
    repository.write(sample_data)
    output_path = os.path.join(temp_dir, "test_export.xlsx")

    repository.export_to_xlsx(output_path)
    assert os.path.exists(output_path)

    # Verify exported data
    exported_data = pd.read_excel(output_path)
    pd.testing.assert_frame_equal(exported_data, sample_data)


def test_export_to_xlsx_with_column_filter(
    repository: CentralDBRepository, temp_dir: str, sample_data: pd.DataFrame
):
    """Test export_to_xlsx() with column filtering."""
    repository.write(sample_data)
    output_path = os.path.join(temp_dir, "filtered_export.xlsx")
    columns_to_export = ["orderCode", "quantity"]

    repository.export_to_xlsx(output_path, columns_to_export)
    assert os.path.exists(output_path)

    # Verify only specified columns are exported
    exported_data = pd.read_excel(output_path)
    expected_data = sample_data[columns_to_export]
    pd.testing.assert_frame_equal(exported_data, expected_data)


def test_export_to_xlsx_with_invalid_columns(
    repository: CentralDBRepository, temp_dir: str, sample_data: pd.DataFrame
):
    """Test export_to_xlsx() with non-existent columns."""
    repository.write(sample_data)
    output_path = os.path.join(temp_dir, "invalid_columns_export.xlsx")
    columns_to_export = ["orderCode", "nonexistent_column"]

    repository.export_to_xlsx(output_path, columns_to_export)
    assert os.path.exists(output_path)

    # Should only export existing columns
    exported_data = pd.read_excel(output_path)
    expected_data = sample_data[["orderCode"]]
    pd.testing.assert_frame_equal(exported_data, expected_data)
