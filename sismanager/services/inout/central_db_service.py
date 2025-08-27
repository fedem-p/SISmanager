"""Repository pattern for central_db.csv file operations."""

from typing import Optional, List
import os
import pandas as pd
from sismanager.config import CENTRAL_DB_PATH, logger


class CentralDBRepository:
    """Handles all file I/O for the central database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CENTRAL_DB_PATH

    def exists(self) -> bool:
        """Check if the central database file exists.

        Returns:
            bool: True if the database file exists, False otherwise.
        """
        return os.path.exists(self.db_path)

    def read(self) -> pd.DataFrame:
        """Read the central database from CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the database contents, empty if file doesn't exist.
        """
        if not self.exists():
            logger.warning("No central_db.csv found.")
            return pd.DataFrame()
        return pd.read_csv(self.db_path)

    def write(self, df: pd.DataFrame) -> None:
        """Write DataFrame to the central database CSV file.

        Args:
            df (pd.DataFrame): DataFrame to write to the database.
        """
        df.to_csv(self.db_path, index=False)

    def append(self, df: pd.DataFrame) -> None:
        """Append DataFrame to the central database CSV file.

        Args:
            df (pd.DataFrame): DataFrame to append to the database.
        """
        if self.exists():
            df.to_csv(self.db_path, mode="a", header=False, index=False)
        else:
            df.to_csv(self.db_path, mode="w", header=True, index=False)

    def deduplicate(self, mode: str = "soft") -> int:
        """Remove duplicate rows from the central database.

        Args:
            mode (str): Deduplication mode. 'soft' prompts for confirmation,
                       'forceful' removes all duplicates automatically.

        Returns:
            int: Number of duplicate rows removed.
        """
        df = self.read()
        if df.empty:
            logger.warning("central_db.csv is empty.")
            return 0
        if mode == "forceful":
            before = len(df)
            df = df.drop_duplicates(keep="first")
            self.write(df)
            logger.info(
                "All duplicates removed forcefully. %d rows deleted.", before - len(df)
            )
            return before - len(df)
        if mode == "soft":
            duplicate_mask = df.duplicated(keep="first")
            to_drop = []
            for idx, is_dup in enumerate(duplicate_mask):
                if is_dup:
                    logger.info(
                        "Duplicate row found (not the first occurrence): %s",
                        df.iloc[idx].to_dict(),
                    )
                    resp = input("Remove this row? [y/N]: ").strip().lower()
                    if resp == "y":
                        to_drop.append(idx)
            before = len(df)
            df = df.drop(index=to_drop)
            self.write(df)
            logger.info(
                "Removed %d duplicates after confirmation. %d rows deleted.",
                len(to_drop),
                before - len(df),
            )
            return len(to_drop)

        logger.error("Unknown mode. Use 'forceful' or 'soft'.")
        return 0

    def export_to_xlsx(
        self, output_path: str, columns: Optional[List[str]] = None
    ) -> None:
        """Export the central database to an XLSX file.

        Args:
            output_path (str): Path where the XLSX file will be saved.
            columns (Optional[List[str]]): List of column names to include.
                                         If None, all columns are exported.
        """
        df = self.read()
        if df.empty:
            logger.warning("No central_db.csv found to export.")
            return
        if columns:
            missing = [col for col in columns if col not in df.columns]
            if missing:
                logger.warning(
                    "Warning: These columns are not in the database and will be ignored: %s",
                    missing,
                )
            df = df[[col for col in columns if col in df.columns]]
        df.to_excel(output_path, index=False)
        logger.info("Exported central_db to %s", output_path)
