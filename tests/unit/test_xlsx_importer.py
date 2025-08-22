"""Unit tests for XLSXImporter."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.xlsx_importer import XLSXImporter
from src.central_db_repository import CentralDBRepository
from src.backup import BackupManager


class TestXLSXImporter(unittest.TestCase):
    """Test cases for XLSXImporter class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_xlsx_path = os.path.join(self.temp_dir, "test_import.xlsx")
        self.test_db_path = os.path.join(self.temp_dir, "test_central_db.csv")
        self.backup_dir = os.path.join(self.temp_dir, "backups")

        # Create sample XLSX file
        self.sample_xlsx_data = pd.DataFrame(
            {
                "idOrderPos": [1, 2, 3],
                "descrizioneMateriale": ["Material A", "Material B", "Material C"],
                "codiceMateriale": ["MAT001", "MAT002", "MAT003"],
                "quantity": [10, 5, 15],
            }
        )
        self.sample_xlsx_data.to_excel(self.test_xlsx_path, index=False)

        # Create mock repository
        self.mock_repository = MagicMock(spec=CentralDBRepository)
        self.mock_repository.db_path = self.test_db_path

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_with_defaults(self):
        """Test XLSXImporter initialization with default parameters."""
        importer = XLSXImporter(self.test_xlsx_path)

        self.assertEqual(importer.xlsx_path, self.test_xlsx_path)
        self.assertEqual(importer.file_name, "test_import.xlsx")
        self.assertEqual(importer.rows, [])
        self.assertIsNone(importer.columns_to_keep)
        self.assertIsInstance(importer.backup_manager, BackupManager)
        self.assertIsInstance(importer.repository, CentralDBRepository)

    def test_init_with_custom_parameters(self):
        """Test XLSXImporter initialization with custom parameters."""
        columns_to_keep = ["idOrderPos", "quantity"]

        importer = XLSXImporter(
            self.test_xlsx_path,
            columns_to_keep=columns_to_keep,
            repository=self.mock_repository,
        )

        self.assertEqual(importer.columns_to_keep, columns_to_keep)
        self.assertEqual(importer.repository, self.mock_repository)

    def test_read_xlsx_success(self):
        """Test successful XLSX reading."""
        importer = XLSXImporter(self.test_xlsx_path)
        importer.read_xlsx()

        self.assertEqual(len(importer.rows), 3)

        # Check that orderCode column was added
        for row in importer.rows:
            self.assertIn("orderCode", row)
            self.assertEqual(
                row["orderCode"], "test_import"
            )  # filename without extension

        # Verify data content
        expected_materials = ["Material A", "Material B", "Material C"]
        actual_materials = [row["descrizioneMateriale"] for row in importer.rows]
        self.assertEqual(actual_materials, expected_materials)

    def test_read_xlsx_with_column_filtering(self):
        """Test XLSX reading with column filtering."""
        columns_to_keep = ["idOrderPos", "quantity"]
        importer = XLSXImporter(self.test_xlsx_path, columns_to_keep=columns_to_keep)
        importer.read_xlsx()

        # Check that only specified columns plus orderCode are present
        for row in importer.rows:
            expected_keys = {"orderCode", "idOrderPos", "quantity"}
            self.assertEqual(set(row.keys()), expected_keys)

    def test_read_xlsx_nonexistent_file(self):
        """Test XLSX reading with non-existent file."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.xlsx")
        importer = XLSXImporter(nonexistent_path)

        with self.assertRaises(Exception):
            importer.read_xlsx()

    def test_read_xlsx_invalid_file(self):
        """Test XLSX reading with invalid file format."""
        # Create a text file with .xlsx extension
        invalid_xlsx = os.path.join(self.temp_dir, "invalid.xlsx")
        with open(invalid_xlsx, "w") as f:
            f.write("This is not an Excel file")

        importer = XLSXImporter(invalid_xlsx)

        with self.assertRaises(Exception):
            importer.read_xlsx()

    @patch.object(BackupManager, "backup_central_db")
    def test_append_to_central_db_success(self, mock_backup):
        """Test successful append to central database."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        importer.rows = [{"orderCode": "TEST", "quantity": 10}]

        # Mock backup directory and files
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_file = os.path.join(self.backup_dir, "central_db_20240115_103045.csv")
        with open(backup_file, "w") as f:
            f.write("test backup")

        with patch.object(importer.backup_manager, "backup_dir", self.backup_dir):
            importer.append_to_central_db()

        # Verify backup was called and repository append was called
        mock_backup.assert_called_once()
        self.mock_repository.append.assert_called_once()

    @patch.object(BackupManager, "backup_central_db")
    def test_append_to_central_db_with_rollback(self, mock_backup):
        """Test append with rollback on failure."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        importer.rows = [{"orderCode": "TEST", "quantity": 10}]

        # Mock backup directory and files
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_file = os.path.join(self.backup_dir, "central_db_20240115_103045.csv")
        with open(backup_file, "w") as f:
            f.write("test backup")

        # Make repository append fail
        self.mock_repository.append.side_effect = Exception("Append failed")

        with patch.object(importer.backup_manager, "backup_dir", self.backup_dir):
            with patch("src.xlsx_importer.shutil.copy2") as mock_copy:
                with self.assertRaises(Exception):
                    importer.append_to_central_db()

                # Verify rollback was attempted
                mock_copy.assert_called_once()

    @patch.object(BackupManager, "backup_central_db")
    def test_process_success(self, mock_backup):
        """Test successful process flow."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)

        # Mock backup directory
        os.makedirs(self.backup_dir, exist_ok=True)

        with patch.object(importer.backup_manager, "backup_dir", self.backup_dir):
            with patch.object(importer, "read_xlsx") as mock_read:
                with patch.object(importer, "append_to_central_db") as mock_append:
                    importer.process()

        # Verify all steps were called
        mock_backup.assert_called_once()
        mock_read.assert_called_once()
        mock_append.assert_called_once()

    def test_process_with_exception(self):
        """Test process flow with exception handling."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)

        with patch.object(importer, "read_xlsx", side_effect=Exception("Read failed")):
            with self.assertRaises(Exception):
                importer.process()

    @patch.object(BackupManager, "backup_central_db")
    def test_remove_duplicates_forceful(self, mock_backup):
        """Test remove_duplicates in forceful mode."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)

        importer.remove_duplicates(mode="forceful")

        mock_backup.assert_called_once()
        self.mock_repository.deduplicate.assert_called_once_with(mode="forceful")

    @patch.object(BackupManager, "backup_central_db")
    def test_remove_duplicates_soft(self, mock_backup):
        """Test remove_duplicates in soft mode."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)

        importer.remove_duplicates(mode="soft")

        mock_backup.assert_called_once()
        self.mock_repository.deduplicate.assert_called_once_with(mode="soft")

    def test_remove_duplicates_with_exception(self):
        """Test remove_duplicates with exception handling."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        self.mock_repository.deduplicate.side_effect = Exception("Deduplicate failed")

        with self.assertRaises(Exception):
            importer.remove_duplicates()

    def test_export_to_xlsx_success(self):
        """Test successful export to XLSX."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        output_path = os.path.join(self.temp_dir, "export.xlsx")
        columns = ["orderCode", "quantity"]

        importer.export_to_xlsx(output_path, columns)

        self.mock_repository.export_to_xlsx.assert_called_once_with(
            output_path, columns
        )

    def test_export_to_xlsx_without_columns(self):
        """Test export to XLSX without specifying columns."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        output_path = os.path.join(self.temp_dir, "export.xlsx")

        importer.export_to_xlsx(output_path)

        self.mock_repository.export_to_xlsx.assert_called_once_with(output_path, None)

    def test_export_to_xlsx_with_exception(self):
        """Test export to XLSX with exception handling."""
        importer = XLSXImporter(self.test_xlsx_path, repository=self.mock_repository)
        self.mock_repository.export_to_xlsx.side_effect = Exception("Export failed")

        with self.assertRaises(Exception):
            importer.export_to_xlsx("output.xlsx")

    def test_ordercode_from_filename(self):
        """Test that orderCode is correctly derived from filename."""
        test_files = [
            ("/path/to/ORDER123.xlsx", "ORDER123"),
            ("/path/to/complex_order_name.xlsx", "complex_order_name"),
            ("simple.xlsx", "simple"),
        ]

        for file_path, expected_order_code in test_files:
            # Create temporary XLSX file with expected name
            temp_xlsx = os.path.join(self.temp_dir, os.path.basename(file_path))
            self.sample_xlsx_data.to_excel(temp_xlsx, index=False)

            importer = XLSXImporter(temp_xlsx)
            importer.read_xlsx()

            for row in importer.rows:
                self.assertEqual(row["orderCode"], expected_order_code)

    def test_empty_xlsx_file(self):
        """Test handling of empty XLSX file."""
        empty_xlsx = os.path.join(self.temp_dir, "empty.xlsx")
        empty_df = pd.DataFrame()
        empty_df.to_excel(empty_xlsx, index=False)

        importer = XLSXImporter(empty_xlsx)
        importer.read_xlsx()

        self.assertEqual(len(importer.rows), 0)


if __name__ == "__main__":
    unittest.main()
