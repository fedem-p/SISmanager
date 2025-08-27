"""Script to run XLSX import, backup cleanup, deduplication, and export for SISmanager."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from sismanager.services.inout.xlsx_importer_service import XLSXImporter
from sismanager.services.inout.backup_service import BackupManager

if __name__ == "__main__":
    # Path to the sample XLSX file in the data directory
    xlsx_path = os.path.join(os.path.dirname(__file__), "../..", "data", "data.xlsx")
    # Example: keep only specific columns
    COLUMNS_TO_KEEP = None  # e.g., ['Name', 'Age']
    importer = XLSXImporter(xlsx_path, columns_to_keep=COLUMNS_TO_KEEP)
    importer.process()

    # Example: delete backups older than 30 days
    backup_manager = BackupManager()
    backup_manager.delete_old_backups(days=30)

    importer.remove_duplicates(mode="forceful")  # or 'soft' to confirm each duplicate

    importer.export_to_xlsx(
        "output.xlsx",
        columns=["orderCode", "idOrderPos", "descrizioneMateriale", "codiceMateriale"],
    )
