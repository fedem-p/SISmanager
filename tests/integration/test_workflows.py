"""Integration tests for SISmanager end-to-end workflows."""

import os
import tempfile
import unittest
import pandas as pd
from unittest.mock import patch

from src.xlsx_importer import XLSXImporter
from src.central_db_repository import CentralDBRepository
from src.backup import BackupManager


class TestIntegrationWorkflows(unittest.TestCase):
    """Integration test cases for complete workflows."""

    def setUp(self):
        """Set up test fixtures before each integration test."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, "data")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        self.central_db_path = os.path.join(self.data_dir, "central_db.csv")

        # Create directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        # Create test XLSX files
        self.create_test_xlsx_files()

        # Initialize components
        self.repository = CentralDBRepository(self.central_db_path)
        self.backup_manager = BackupManager(self.backup_dir, self.central_db_path)

    def tearDown(self):
        """Clean up after each integration test."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_xlsx_files(self):
        """Create test XLSX files for integration testing."""
        # First order file
        order1_data = pd.DataFrame(
            {
                "idOrderPos": [1, 2, 3],
                "descrizioneMateriale": ["Material A", "Material B", "Material C"],
                "codiceMateriale": ["MAT001", "MAT002", "MAT003"],
                "quantity": [10, 5, 15],
            }
        )
        self.order1_path = os.path.join(self.data_dir, "ORDER001.xlsx")
        order1_data.to_excel(self.order1_path, index=False)

        # Second order file
        order2_data = pd.DataFrame(
            {
                "idOrderPos": [1, 2],
                "descrizioneMateriale": ["Material D", "Material A"],
                "codiceMateriale": ["MAT004", "MAT001"],
                "quantity": [20, 12],
            }
        )
        self.order2_path = os.path.join(self.data_dir, "ORDER002.xlsx")
        order2_data.to_excel(self.order2_path, index=False)

        # File with duplicate data (for deduplication testing)
        duplicate_data = pd.DataFrame(
            {
                "idOrderPos": [1, 1, 2],
                "descrizioneMateriale": ["Material A", "Material A", "Material B"],
                "codiceMateriale": ["MAT001", "MAT001", "MAT002"],
                "quantity": [10, 10, 5],
            }
        )
        self.duplicate_path = os.path.join(self.data_dir, "DUPLICATE_ORDER.xlsx")
        duplicate_data.to_excel(self.duplicate_path, index=False)

    def test_complete_import_workflow(self):
        """Test complete import workflow from XLSX to central database."""
        # Import first order
        importer1 = XLSXImporter(self.order1_path, repository=self.repository)
        importer1.process()

        # Verify data was imported
        self.assertTrue(self.repository.exists())
        data = self.repository.read()
        self.assertEqual(len(data), 3)
        self.assertTrue(all(data["orderCode"] == "ORDER001"))

        # Import second order
        importer2 = XLSXImporter(self.order2_path, repository=self.repository)
        importer2.process()

        # Verify both orders are in database
        data = self.repository.read()
        self.assertEqual(len(data), 5)  # 3 + 2 records

        order_codes = data["orderCode"].unique()
        self.assertIn("ORDER001", order_codes)
        self.assertIn("ORDER002", order_codes)

    def test_backup_and_rollback_workflow(self):
        """Test backup creation and rollback functionality."""
        # Create initial data
        initial_data = pd.DataFrame(
            {
                "orderCode": ["INITIAL"],
                "idOrderPos": [1],
                "descrizioneMateriale": ["Initial Material"],
                "codiceMateriale": ["INIT001"],
                "quantity": [5],
            }
        )
        self.repository.write(initial_data)

        # Create backup
        self.backup_manager.backup_central_db()

        # Verify backup was created
        backup_files = [
            f for f in os.listdir(self.backup_dir) if f.startswith("central_db_")
        ]
        self.assertEqual(len(backup_files), 1)

        # Modify database
        modified_data = pd.DataFrame(
            {
                "orderCode": ["MODIFIED"],
                "idOrderPos": [1],
                "descrizioneMateriale": ["Modified Material"],
                "codiceMateriale": ["MOD001"],
                "quantity": [10],
            }
        )
        self.repository.write(modified_data)

        # Verify modification
        current_data = self.repository.read()
        self.assertEqual(current_data.iloc[0]["orderCode"], "MODIFIED")

        # Simulate rollback by restoring backup
        backup_path = os.path.join(self.backup_dir, backup_files[0])
        import shutil

        shutil.copy2(backup_path, self.central_db_path)

        # Verify rollback
        restored_data = self.repository.read()
        self.assertEqual(restored_data.iloc[0]["orderCode"], "INITIAL")

    def test_deduplication_workflow(self):
        """Test end-to-end deduplication workflow."""
        # Import file with duplicates
        importer = XLSXImporter(self.duplicate_path, repository=self.repository)
        importer.process()

        # Verify duplicates exist
        data = self.repository.read()
        self.assertEqual(len(data), 3)  # Original has 3 rows including duplicates
        duplicates = data.duplicated()
        self.assertTrue(duplicates.any())

        # Remove duplicates forcefully
        removed_count = self.repository.deduplicate(mode="forceful")
        self.assertGreater(removed_count, 0)

        # Verify duplicates removed
        final_data = self.repository.read()
        self.assertFalse(final_data.duplicated().any())
        self.assertLess(len(final_data), 3)

    def test_export_workflow(self):
        """Test end-to-end export workflow."""
        # Import some data first
        importer = XLSXImporter(self.order1_path, repository=self.repository)
        importer.process()

        # Export to XLSX
        export_path = os.path.join(self.temp_dir, "exported_data.xlsx")
        self.repository.export_to_xlsx(export_path)

        # Verify export file exists and contains correct data
        self.assertTrue(os.path.exists(export_path))
        exported_data = pd.read_excel(export_path)

        # Compare with original data
        original_data = self.repository.read()
        pd.testing.assert_frame_equal(exported_data, original_data)

    def test_filtered_export_workflow(self):
        """Test export workflow with column filtering."""
        # Import data
        importer = XLSXImporter(self.order1_path, repository=self.repository)
        importer.process()

        # Export only specific columns
        columns_to_export = ["orderCode", "descrizioneMateriale", "quantity"]
        export_path = os.path.join(self.temp_dir, "filtered_export.xlsx")
        self.repository.export_to_xlsx(export_path, columns_to_export)

        # Verify filtered export
        self.assertTrue(os.path.exists(export_path))
        exported_data = pd.read_excel(export_path)

        self.assertEqual(list(exported_data.columns), columns_to_export)
        self.assertEqual(len(exported_data), 3)  # Should have same number of rows

    def test_multiple_import_and_backup_cleanup_workflow(self):
        """Test workflow with multiple imports and backup cleanup."""
        # Create initial database to enable backups
        initial_data = pd.DataFrame(
            {
                "orderCode": ["INIT"],
                "idOrderPos": [0],
                "descrizioneMateriale": ["Initial"],
                "codiceMateriale": ["INIT"],
                "quantity": [1],
            }
        )
        self.repository.write(initial_data)

        # Verify the database file exists
        self.assertTrue(self.repository.exists())

        # Perform multiple imports to create multiple backups
        backup_count = 0
        for i, xlsx_path in enumerate(
            [self.order1_path, self.order2_path, self.duplicate_path]
        ):
            importer = XLSXImporter(xlsx_path, repository=self.repository)

            # Use the same backup manager as the one that has the correct paths
            importer.backup_manager = self.backup_manager

            importer.process()

            # Count backup files after each import
            backup_files = [
                f for f in os.listdir(self.backup_dir) if f.startswith("central_db_")
            ]
            current_backup_count = len(backup_files)
            self.assertGreaterEqual(current_backup_count, backup_count)
            backup_count = current_backup_count

        # Test backup cleanup (should not delete recent backups)
        deleted_count, freed_space = self.backup_manager.delete_old_backups(days=30)
        self.assertEqual(deleted_count, 0)  # No old backups to delete

        # Verify data integrity after all operations
        final_data = self.repository.read()
        self.assertGreater(len(final_data), 1)  # Should have initial + imported data

        # Should have data from all three imported files plus initial
        expected_order_codes = {"INIT", "ORDER001", "ORDER002", "DUPLICATE_ORDER"}
        actual_order_codes = set(final_data["orderCode"].unique())
        self.assertEqual(actual_order_codes, expected_order_codes)

    @patch("builtins.input", return_value="n")  # Always say no to duplicate removal
    def test_soft_deduplication_workflow(self, mock_input):
        """Test soft deduplication workflow with user interaction."""
        # Import file with duplicates
        importer = XLSXImporter(self.duplicate_path, repository=self.repository)
        importer.process()

        # Remove duplicates in soft mode (user says no to all)
        removed_count = self.repository.deduplicate(mode="soft")
        self.assertEqual(removed_count, 0)  # No duplicates removed due to user input

        # Data should still contain duplicates
        data = self.repository.read()
        self.assertTrue(data.duplicated().any())

    def test_error_recovery_workflow(self):
        """Test error recovery and rollback in case of failures."""
        # Create initial data
        initial_data = pd.DataFrame(
            {
                "orderCode": ["INITIAL"],
                "idOrderPos": [1],
                "descrizioneMateriale": ["Initial Material"],
                "codiceMateriale": ["INIT001"],
                "quantity": [5],
            }
        )
        self.repository.write(initial_data)

        # Create a backup first to have something to rollback to
        self.backup_manager.backup_central_db()

        # Verify backup was created
        backup_files = [
            f for f in os.listdir(self.backup_dir) if f.startswith("central_db_")
        ]
        self.assertGreater(len(backup_files), 0)
        backup_path = os.path.join(self.backup_dir, backup_files[0])

        # Create a mock repository that fails on append
        mock_repository = CentralDBRepository(self.central_db_path)

        # Mock the append method to fail
        def failing_append(df):
            raise Exception("Simulated append failure")

        importer = XLSXImporter(self.order1_path, repository=mock_repository)

        # Replace append method and try to process (should fail)
        mock_repository.append = failing_append
        importer.read_xlsx()  # This should work

        try:
            importer.append_to_central_db()  # This should fail and trigger rollback
        except Exception:
            pass  # Expected to fail

        # Verify that data wasn't corrupted (rollback should have happened)
        # The append_to_central_db method should handle the rollback
        final_data = self.repository.read()

        # Should still have initial data (rollback occurred)
        self.assertEqual(len(final_data), 1)
        self.assertEqual(final_data.iloc[0]["orderCode"], "INITIAL")

    def test_column_filtering_workflow(self):
        """Test workflow with column filtering during import."""
        columns_to_keep = ["idOrderPos", "quantity"]

        importer = XLSXImporter(
            self.order1_path,
            columns_to_keep=columns_to_keep,
            repository=self.repository,
        )
        importer.process()

        # Verify only specified columns plus orderCode are in database
        data = self.repository.read()
        expected_columns = {"orderCode", "idOrderPos", "quantity"}
        self.assertEqual(set(data.columns), expected_columns)

        # Verify data content
        self.assertEqual(len(data), 3)
        self.assertTrue(all(data["orderCode"] == "ORDER001"))


if __name__ == "__main__":
    unittest.main()
