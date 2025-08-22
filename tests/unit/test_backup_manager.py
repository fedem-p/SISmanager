"""Unit tests for BackupManager."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.backup import BackupManager


class TestBackupManager(unittest.TestCase):
    """Test cases for BackupManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.test_db_path = os.path.join(self.temp_dir, "test_db.csv")
        self.backup_manager = BackupManager(self.backup_dir, self.test_db_path)

        # Create test database file
        with open(self.test_db_path, "w") as f:
            f.write("orderCode,quantity\nORDER001,10\nORDER002,5\n")

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_creates_backup_dir(self):
        """Test that initialization creates backup directory."""
        self.assertTrue(os.path.exists(self.backup_dir))

    def test_init_with_default_paths(self):
        """Test initialization with default paths."""
        manager = BackupManager()
        self.assertIsNotNone(manager.backup_dir)
        self.assertIsNotNone(manager.db_path)

    def test_file_hash_valid_file(self):
        """Test _file_hash() with valid file."""
        expected_hash = self.backup_manager._file_hash(self.test_db_path)
        self.assertIsInstance(expected_hash, str)
        self.assertEqual(len(expected_hash), 64)  # SHA256 produces 64-char hex string

    def test_file_hash_nonexistent_file(self):
        """Test _file_hash() with non-existent file."""
        with self.assertRaises(Exception):
            self.backup_manager._file_hash("/nonexistent/file.csv")

    @patch("src.backup.datetime")
    def test_backup_central_db_success(self, mock_datetime):
        """Test successful backup creation."""
        # Mock datetime to return consistent timestamp
        mock_now = mock_datetime.now.return_value
        mock_now.strftime.return_value = "20240115_103045"

        self.backup_manager.backup_central_db()

        # Check if backup file was created
        expected_backup_name = "central_db_20240115_103045.csv"
        backup_path = os.path.join(self.backup_dir, expected_backup_name)
        self.assertTrue(os.path.exists(backup_path))

        # Verify backup content matches original
        with open(self.test_db_path, "r") as orig:
            original_content = orig.read()
        with open(backup_path, "r") as backup:
            backup_content = backup.read()
        self.assertEqual(original_content, backup_content)

    def test_backup_central_db_no_source_file(self):
        """Test backup when source database doesn't exist."""
        os.remove(self.test_db_path)

        # Should not raise exception, just log warning
        self.backup_manager.backup_central_db()

        # No backup files should be created
        backup_files = os.listdir(self.backup_dir)
        self.assertEqual(len(backup_files), 0)

    @patch("src.backup.shutil.copy2")
    def test_backup_central_db_copy_failure(self, mock_copy):
        """Test backup when file copy fails."""
        mock_copy.side_effect = IOError("Copy failed")

        with self.assertRaises(IOError):
            self.backup_manager.backup_central_db()

    @patch("src.backup.BackupManager._file_hash")
    def test_backup_verification_failure(self, mock_hash):
        """Test backup when verification fails."""
        # Make hash verification fail
        mock_hash.side_effect = ["hash1", "hash2"]  # Different hashes

        with self.assertRaises(RuntimeError):
            self.backup_manager.backup_central_db()

    def test_delete_old_backups_no_files(self):
        """Test delete_old_backups() when no files exist."""
        deleted_count, freed_space = self.backup_manager.delete_old_backups(days=30)
        self.assertEqual(deleted_count, 0)
        self.assertEqual(freed_space, 0)

    def test_delete_old_backups_with_old_files(self):
        """Test delete_old_backups() with files older than threshold."""
        # Create old backup files
        old_backup1 = os.path.join(self.backup_dir, "old_backup1.csv")
        old_backup2 = os.path.join(self.backup_dir, "old_backup2.csv")
        recent_backup = os.path.join(self.backup_dir, "recent_backup.csv")

        # Create files with content
        for backup_file in [old_backup1, old_backup2, recent_backup]:
            with open(backup_file, "w") as f:
                f.write("test content")

        # Modify timestamps to simulate old files
        old_time = datetime.now() - timedelta(days=35)
        old_timestamp = old_time.timestamp()

        os.utime(old_backup1, (old_timestamp, old_timestamp))
        os.utime(old_backup2, (old_timestamp, old_timestamp))

        # Delete files older than 30 days
        deleted_count, freed_space = self.backup_manager.delete_old_backups(days=30)

        self.assertEqual(deleted_count, 2)
        self.assertGreater(freed_space, 0)
        self.assertFalse(os.path.exists(old_backup1))
        self.assertFalse(os.path.exists(old_backup2))
        self.assertTrue(os.path.exists(recent_backup))

    def test_delete_old_backups_with_recent_files(self):
        """Test delete_old_backups() with only recent files."""
        # Create recent backup file
        recent_backup = os.path.join(self.backup_dir, "recent_backup.csv")
        with open(recent_backup, "w") as f:
            f.write("test content")

        deleted_count, freed_space = self.backup_manager.delete_old_backups(days=30)

        self.assertEqual(deleted_count, 0)
        self.assertEqual(freed_space, 0)
        self.assertTrue(os.path.exists(recent_backup))

    @patch("src.backup.os.listdir")
    def test_delete_old_backups_exception_handling(self, mock_listdir):
        """Test delete_old_backups() exception handling."""
        mock_listdir.side_effect = OSError("Permission denied")

        with self.assertRaises(OSError):
            self.backup_manager.delete_old_backups(days=30)

    def test_delete_old_backups_ignores_directories(self):
        """Test delete_old_backups() ignores subdirectories."""
        # Create a subdirectory
        subdir = os.path.join(self.backup_dir, "subdir")
        os.makedirs(subdir)

        # Create old file in subdirectory
        old_file = os.path.join(subdir, "file_in_subdir.csv")
        with open(old_file, "w") as f:
            f.write("test")

        # Modify timestamp to be old
        old_time = datetime.now() - timedelta(days=35)
        old_timestamp = old_time.timestamp()
        os.utime(subdir, (old_timestamp, old_timestamp))

        deleted_count, freed_space = self.backup_manager.delete_old_backups(days=30)

        # Should not delete directories, only files
        self.assertEqual(deleted_count, 0)
        self.assertTrue(os.path.exists(subdir))

    def test_backup_integrity_with_different_file_sizes(self):
        """Test backup integrity check with files of different sizes."""
        # Create a backup first
        self.backup_manager.backup_central_db()

        # Verify backup exists
        backup_files = [
            f for f in os.listdir(self.backup_dir) if f.startswith("central_db_")
        ]
        self.assertEqual(len(backup_files), 1)

        # Verify integrity by checking sizes match
        backup_path = os.path.join(self.backup_dir, backup_files[0])
        original_size = os.path.getsize(self.test_db_path)
        backup_size = os.path.getsize(backup_path)
        self.assertEqual(original_size, backup_size)


if __name__ == "__main__":
    unittest.main()
