"""Unit tests for CentralDBRepository."""

import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
import pandas as pd

from src.central_db_repository import CentralDBRepository


class TestCentralDBRepository(unittest.TestCase):
    """Test cases for CentralDBRepository class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_central_db.csv")
        self.repository = CentralDBRepository(self.test_db_path)

        # Sample test data
        self.sample_data = pd.DataFrame(
            {
                "orderCode": ["ORDER001", "ORDER002", "ORDER003"],
                "idOrderPos": [1, 2, 3],
                "descrizioneMateriale": ["Material A", "Material B", "Material C"],
                "codiceMateriale": ["MAT001", "MAT002", "MAT003"],
                "quantity": [10, 5, 15],
            }
        )

        self.duplicate_data = pd.DataFrame(
            {
                "orderCode": ["ORDER001", "ORDER001", "ORDER002"],
                "idOrderPos": [1, 1, 2],
                "descrizioneMateriale": ["Material A", "Material A", "Material B"],
                "codiceMateriale": ["MAT001", "MAT001", "MAT002"],
                "quantity": [10, 10, 5],
            }
        )

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_default_path(self):
        """Test repository initialization with default path."""
        repo = CentralDBRepository()
        self.assertIsNotNone(repo.db_path)

    def test_init_custom_path(self):
        """Test repository initialization with custom path."""
        custom_path = "/custom/path/db.csv"
        repo = CentralDBRepository(custom_path)
        self.assertEqual(repo.db_path, custom_path)

    def test_exists_file_not_exists(self):
        """Test exists() when file doesn't exist."""
        self.assertFalse(self.repository.exists())

    def test_exists_file_exists(self):
        """Test exists() when file exists."""
        self.sample_data.to_csv(self.test_db_path, index=False)
        self.assertTrue(self.repository.exists())

    def test_read_empty_file(self):
        """Test read() when file doesn't exist."""
        result = self.repository.read()
        self.assertTrue(result.empty)

    def test_read_existing_file(self):
        """Test read() when file exists."""
        self.sample_data.to_csv(self.test_db_path, index=False)
        result = self.repository.read()
        pd.testing.assert_frame_equal(result, self.sample_data)

    def test_write(self):
        """Test write() functionality."""
        self.repository.write(self.sample_data)
        self.assertTrue(os.path.exists(self.test_db_path))

        # Verify written data
        written_data = pd.read_csv(self.test_db_path)
        pd.testing.assert_frame_equal(written_data, self.sample_data)

    def test_append_to_new_file(self):
        """Test append() to a new file (should create with headers)."""
        self.repository.append(self.sample_data)
        self.assertTrue(os.path.exists(self.test_db_path))

        written_data = pd.read_csv(self.test_db_path)
        pd.testing.assert_frame_equal(written_data, self.sample_data)

    def test_append_to_existing_file(self):
        """Test append() to an existing file."""
        # First write some data
        initial_data = self.sample_data.iloc[:2]
        self.repository.write(initial_data)

        # Then append more data
        new_data = self.sample_data.iloc[2:]
        self.repository.append(new_data)

        # Verify combined data
        result = self.repository.read()
        pd.testing.assert_frame_equal(result, self.sample_data)

    def test_deduplicate_empty_dataframe(self):
        """Test deduplicate() with empty dataframe."""
        result = self.repository.deduplicate()
        self.assertEqual(result, 0)

    def test_deduplicate_forceful_mode(self):
        """Test deduplicate() in forceful mode."""
        self.repository.write(self.duplicate_data)

        result = self.repository.deduplicate(mode="forceful")
        self.assertEqual(result, 1)  # Should remove 1 duplicate

        # Verify duplicates are removed
        final_data = self.repository.read()
        self.assertEqual(len(final_data), 2)
        self.assertFalse(final_data.duplicated().any())

    @patch("builtins.input", side_effect=["y", "n"])
    def test_deduplicate_soft_mode(self, mock_input):
        """Test deduplicate() in soft mode with user confirmation."""
        self.repository.write(self.duplicate_data)

        result = self.repository.deduplicate(mode="soft")
        self.assertEqual(
            result, 1
        )  # Should remove 1 duplicate (user said 'y' to first, 'n' to second)

    def test_deduplicate_invalid_mode(self):
        """Test deduplicate() with invalid mode."""
        self.repository.write(self.duplicate_data)

        result = self.repository.deduplicate(mode="invalid")
        self.assertEqual(result, 0)

    def test_export_to_xlsx_empty_dataframe(self):
        """Test export_to_xlsx() with empty dataframe."""
        output_path = os.path.join(self.temp_dir, "empty_export.xlsx")

        # Should not create file and should not raise exception
        self.repository.export_to_xlsx(output_path)
        self.assertFalse(os.path.exists(output_path))

    def test_export_to_xlsx_with_data(self):
        """Test export_to_xlsx() with data."""
        self.repository.write(self.sample_data)
        output_path = os.path.join(self.temp_dir, "test_export.xlsx")

        self.repository.export_to_xlsx(output_path)
        self.assertTrue(os.path.exists(output_path))

        # Verify exported data
        exported_data = pd.read_excel(output_path)
        pd.testing.assert_frame_equal(exported_data, self.sample_data)

    def test_export_to_xlsx_with_column_filter(self):
        """Test export_to_xlsx() with column filtering."""
        self.repository.write(self.sample_data)
        output_path = os.path.join(self.temp_dir, "filtered_export.xlsx")
        columns_to_export = ["orderCode", "quantity"]

        self.repository.export_to_xlsx(output_path, columns_to_export)
        self.assertTrue(os.path.exists(output_path))

        # Verify only specified columns are exported
        exported_data = pd.read_excel(output_path)
        expected_data = self.sample_data[columns_to_export]
        pd.testing.assert_frame_equal(exported_data, expected_data)

    def test_export_to_xlsx_with_invalid_columns(self):
        """Test export_to_xlsx() with non-existent columns."""
        self.repository.write(self.sample_data)
        output_path = os.path.join(self.temp_dir, "invalid_columns_export.xlsx")
        columns_to_export = ["orderCode", "nonexistent_column"]

        self.repository.export_to_xlsx(output_path, columns_to_export)
        self.assertTrue(os.path.exists(output_path))

        # Should only export existing columns
        exported_data = pd.read_excel(output_path)
        expected_data = self.sample_data[["orderCode"]]
        pd.testing.assert_frame_equal(exported_data, expected_data)


if __name__ == "__main__":
    unittest.main()
