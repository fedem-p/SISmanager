"""Backup management for SISmanager: handles backup creation, verification, and cleanup."""

import hashlib
import os
import shutil
from datetime import datetime, timedelta

from sismanager.config import CENTRAL_DB_PATH, BACKUP_DIR, logger


class BackupManager:
    """Manages backups of the central database, including creation, verification, and cleanup."""

    def __init__(self, backup_dir: str = BACKUP_DIR, db_path: str = CENTRAL_DB_PATH):
        """Initialize BackupManager with backup directory and database path."""
        self.backup_dir = backup_dir
        self.db_path = db_path
        os.makedirs(self.backup_dir, exist_ok=True)

    def _file_hash(self, path):
        """Compute SHA256 hash of a file for integrity check."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Failed to compute hash for %s: %s", path, e)
            raise

    def backup_central_db(self):
        """Create a timestamped backup of the central database and verify its integrity."""
        try:
            if os.path.exists(self.db_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"central_db_{timestamp}.csv"
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(self.db_path, backup_path)
                # Verification: check file size and hash
                src_size = os.path.getsize(self.db_path)
                backup_size = os.path.getsize(backup_path)
                src_hash = self._file_hash(self.db_path)
                backup_hash = self._file_hash(backup_path)
                if src_size == backup_size and src_hash == backup_hash:
                    logger.info("Backup created and verified: %s", backup_path)
                else:
                    logger.error("Backup verification FAILED for: %s", backup_path)
                    os.remove(backup_path)
                    raise RuntimeError(
                        "Backup verification failed. Backup file removed."
                    )
            else:
                logger.warning("No central_db.csv to backup.")
        except Exception as e:
            logger.error("Error during backup: %s", e)
            raise

    def delete_old_backups(self, days: int = 30):
        """Delete backups older than the specified number of days."""
        now = datetime.now()
        total_freed = 0
        deleted_files = 0
        try:
            for fname in os.listdir(self.backup_dir):
                fpath = os.path.join(self.backup_dir, fname)
                if os.path.isfile(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if (now - mtime) > timedelta(days=days):
                        size = os.path.getsize(fpath)
                        os.remove(fpath)
                        total_freed += size
                        deleted_files += 1
            logger.info(
                "Deleted %d backups, freed %.2f MB.",
                deleted_files,
                total_freed / 1024 / 1024,
            )
            return deleted_files, total_freed
        except Exception as e:
            logger.error("Error deleting old backups: %s", e)
            raise
