"""XLSX import, append, and deduplication logic for SISmanager."""

import os
import shutil
from typing import List, Optional

import pandas as pd
from tqdm import tqdm

from sismanager.services.inout.backup_service import BackupManager
from sismanager.config import logger
from sismanager.services.inout.central_db_service import CentralDBRepository


class XLSXImporter:
    """Handles importing XLSX files, appending to central DB, and removing duplicates."""

    rows: list[dict]

    def __init__(
        self,
        xlsx_path: str,
        columns_to_keep: Optional[List[str]] = None,
        repository: Optional[CentralDBRepository] = None,
        original_filename: Optional[str] = None,
    ):
        """Initialize with XLSX file path, optional columns to keep, and repository (DI)."""
        self.xlsx_path = xlsx_path
        self.file_name = os.path.basename(xlsx_path)
        self.original_filename = original_filename
        self.rows = []
        self.columns_to_keep = columns_to_keep
        self.backup_manager = BackupManager()
        self.repository = repository or CentralDBRepository()

    def read_xlsx(self):
        """Read the XLSX file and store rows as dicts, with progress bar."""
        try:
            df = pd.read_excel(self.xlsx_path)
            if self.columns_to_keep:
                df = df[self.columns_to_keep]
            # Add orderCode column with the original file name (without extension) as the first column
            order_code = os.path.splitext(self.original_filename or self.file_name)[0]
            df.insert(0, "orderCode", order_code)
            # Progress bar for converting to dict
            self.rows = []
            for row in tqdm(df.to_dict(orient="records"), desc="Processing rows"):
                self.rows.append(row)
        except Exception as e:
            logger.error("Error reading XLSX file %s: %s", self.xlsx_path, e)
            raise

    def append_to_central_db(self):
        """Append rows to the central DB using repository and transaction-like approach."""
        df = pd.DataFrame(self.rows)
        backup_path = None
        try:
            # Backup before modifying
            self.backup_manager.backup_central_db()
            # Find the latest backup for rollback if needed
            backup_files = sorted(
                [
                    os.path.join(self.backup_manager.backup_dir, f)
                    for f in os.listdir(self.backup_manager.backup_dir)
                    if f.startswith("central_db_") and f.endswith(".csv")
                ],
                reverse=True,
            )
            backup_path = backup_files[0] if backup_files else None

            # Use repository for append
            self.repository.append(df)
            logger.info("Appended %d rows to central_db.csv", len(df))
        except Exception as e:
            logger.error("Error during append: %s", e)
            # Rollback: restore from backup if available
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, self.repository.db_path)
                logger.warning("Rolled back to backup: %s", backup_path)
            raise

    def process(self):
        """Process the XLSX file: backup, read, and append to central DB."""
        try:
            # Backup before modifying central db
            self.backup_manager.backup_central_db()
            self.read_xlsx()
            self.append_to_central_db()
            logger.info(
                "Processed %d rows from %s into central_db.csv",
                len(self.rows),
                self.file_name,
            )
        except Exception as e:
            logger.error("Error processing %s: %s", self.file_name, e)
            raise

    def remove_duplicates(self, mode: str = "soft"):
        """
        Remove duplicates from the central DB. 'forceful' removes all, 'soft' asks for confirmation.

        mode: 'forceful' removes all duplicates automatically.
              'soft' asks for confirmation before removing
                        each duplicate row (except the first occurrence).
        """
        try:
            self.backup_manager.backup_central_db()
            self.repository.deduplicate(mode=mode)
        except Exception as e:
            logger.error("Error removing duplicates: %s", e)
            raise

    def export_to_xlsx(self, output_path: str, columns: Optional[List[str]] = None):
        """
        Export the central DB to XLSX, optionally filtering columns.

        columns: List of column names to include in the export. If None, all columns are included.
        """
        try:
            self.repository.export_to_xlsx(output_path, columns)
        except Exception as e:
            logger.error("Error exporting to XLSX: %s", e)
            raise
