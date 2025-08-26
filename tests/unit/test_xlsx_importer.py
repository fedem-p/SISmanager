"""Unit tests for XLSXImporter."""

import os
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from src.xlsx_importer import XLSXImporter
from src.central_db_repository import CentralDBRepository
from src.backup import BackupManager


@pytest.fixture
def test_xlsx_path(temp_dir: str, sample_xlsx_data: pd.DataFrame) -> str:
    """Create test XLSX file."""
    xlsx_path = os.path.join(temp_dir, "test_import.xlsx")
    sample_xlsx_data.to_excel(xlsx_path, index=False)
    return xlsx_path


@pytest.fixture
def test_db_path(temp_dir: str) -> str:
    """Create test database path."""
    return os.path.join(temp_dir, "test_central_db.csv")


@pytest.fixture
def mock_repository(test_db_path: str) -> MagicMock:
    """Create mock repository."""
    mock_repo = MagicMock(spec=CentralDBRepository)
    mock_repo.db_path = test_db_path
    return mock_repo


def test_init_with_defaults(test_xlsx_path: str):
    """Test XLSXImporter initialization with default parameters."""
    importer = XLSXImporter(test_xlsx_path)

    assert importer.xlsx_path == test_xlsx_path
    assert importer.repository is not None
    assert importer.backup_manager is not None
    assert importer.columns_to_keep is None


def test_init_with_custom_parameters(test_xlsx_path: str, mock_repository: MagicMock):
    """Test XLSXImporter initialization with custom parameters."""
    columns = ["idOrderPos", "quantity"]

    importer = XLSXImporter(
        test_xlsx_path, columns_to_keep=columns, repository=mock_repository
    )

    assert importer.xlsx_path == test_xlsx_path
    assert importer.columns_to_keep == columns
    assert importer.repository == mock_repository


def test_read_xlsx_success(test_xlsx_path: str, sample_xlsx_data: pd.DataFrame):
    """Test successful XLSX reading."""
    importer = XLSXImporter(test_xlsx_path)

    importer.read_xlsx()

    # Should have added orderCode column and converted to rows
    assert len(importer.rows) == len(sample_xlsx_data)
    assert "orderCode" in importer.rows[0]
    assert importer.rows[0]["orderCode"] == "test_import"


def test_read_xlsx_nonexistent_file():
    """Test reading non-existent XLSX file."""
    importer = XLSXImporter("/nonexistent/file.xlsx")

    with pytest.raises(Exception):
        importer.read_xlsx()


def test_read_xlsx_with_column_filtering(test_xlsx_path: str):
    """Test XLSX reading with column filtering."""
    columns_to_keep = ["idOrderPos", "quantity"]

    importer = XLSXImporter(test_xlsx_path, columns_to_keep=columns_to_keep)
    importer.read_xlsx()

    # Should have orderCode plus the filtered columns
    expected_columns = ["orderCode"] + columns_to_keep
    for row in importer.rows:
        assert len(row) == len(expected_columns)
        for col in expected_columns:
            assert col in row


def test_empty_xlsx_file(temp_dir: str):
    """Test reading empty XLSX file."""
    empty_xlsx_path = os.path.join(temp_dir, "empty.xlsx")
    empty_df = pd.DataFrame()
    empty_df.to_excel(empty_xlsx_path, index=False)

    importer = XLSXImporter(empty_xlsx_path)
    importer.read_xlsx()

    # Should still add orderCode but have no data rows
    assert len(importer.rows) == 0


def test_remove_duplicates_soft(mock_repository: MagicMock):
    """Test remove_duplicates with soft mode."""
    importer = XLSXImporter("dummy.xlsx", repository=mock_repository)
    mock_repository.deduplicate.return_value = 1

    # Method doesn't return a value, just calls repository.deduplicate
    importer.remove_duplicates(mode="soft")

    mock_repository.deduplicate.assert_called_once_with(mode="soft")


def test_remove_duplicates_forceful(mock_repository: MagicMock):
    """Test remove_duplicates with forceful mode."""
    importer = XLSXImporter("dummy.xlsx", repository=mock_repository)
    mock_repository.deduplicate.return_value = 2

    # Method doesn't return a value, just calls repository.deduplicate
    importer.remove_duplicates(mode="forceful")

    mock_repository.deduplicate.assert_called_once_with(mode="forceful")


def test_append_to_central_db_success(
    mock_repository: MagicMock, sample_xlsx_data: pd.DataFrame
):
    """Test successful append to central database."""
    importer = XLSXImporter("dummy.xlsx", repository=mock_repository)
    # Convert sample data to rows format
    importer.rows = sample_xlsx_data.to_dict(orient="records")

    importer.append_to_central_db()

    mock_repository.append.assert_called_once()
    # Check that DataFrame was passed to append
    call_args = mock_repository.append.call_args[0][0]
    assert isinstance(call_args, pd.DataFrame)


@patch.object(XLSXImporter, "read_xlsx")
@patch.object(XLSXImporter, "append_to_central_db")
def test_process_success(mock_append, mock_read, sample_xlsx_data: pd.DataFrame):
    """Test successful process execution."""
    importer = XLSXImporter("dummy.xlsx")
    # Simulate rows being populated by read_xlsx
    importer.rows = sample_xlsx_data.to_dict(orient="records")

    # Process method doesn't return anything, just executes the workflow
    importer.process()

    mock_read.assert_called_once()
    mock_append.assert_called_once()


@patch.object(XLSXImporter, "read_xlsx")
def test_process_with_exception(mock_read):
    """Test process with exception."""
    mock_read.side_effect = Exception("Read failed")

    importer = XLSXImporter("dummy.xlsx")

    with pytest.raises(Exception):
        importer.process()


def test_export_to_xlsx_success(
    mock_repository: MagicMock, temp_dir: str, sample_data: pd.DataFrame
):
    """Test successful export to XLSX."""
    export_path = os.path.join(temp_dir, "export.xlsx")

    importer = XLSXImporter("dummy.xlsx", repository=mock_repository)
    importer.export_to_xlsx(export_path)

    mock_repository.export_to_xlsx.assert_called_once_with(export_path, None)


def test_export_to_xlsx_with_columns(mock_repository: MagicMock, temp_dir: str):
    """Test export to XLSX with specific columns."""
    export_path = os.path.join(temp_dir, "export.xlsx")
    columns = ["orderCode", "quantity"]

    importer = XLSXImporter("dummy.xlsx", repository=mock_repository)
    importer.export_to_xlsx(export_path, columns)

    mock_repository.export_to_xlsx.assert_called_once_with(export_path, columns)
