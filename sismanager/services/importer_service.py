"""
High-level service for orchestrating file import workflows in SISmanager.

This service provides a simplified interface for the complete import process,
abstracting away the complexity from route handlers and reducing client-side logic.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

from sismanager.config import logger
from sismanager.services.file_manager import file_manager
from sismanager.services.inout.xlsx_importer_service import XLSXImporter
from sismanager.services.inout.central_db_service import CentralDBRepository


class ImporterService:
    """High-level service for managing the complete file import workflow."""

    def __init__(self):
        """Initialize the service with required dependencies."""
        self.file_manager = file_manager
        self.repository = CentralDBRepository()

    def upload_files(self, files: List[Any]) -> Dict[str, Any]:
        """
        Upload and validate multiple files.
        
        Args:
            files: List of werkzeug FileStorage objects
            
        Returns:
            Dict containing upload results and file metadata
        """
        if not files or all(file.filename == "" for file in files):
            return {
                "success": False,
                "message": "No files selected",
                "files": [],
                "errors": ["No files provided"]
            }

        uploaded_files = []
        errors = []

        for file in files:
            if not file or file.filename == "":
                continue

            try:
                # Validate file through file_manager (it handles validation)
                file_metadata = self.file_manager.store_uploaded_file(file, file.filename)
                uploaded_files.append({
                    "file_id": file_metadata["id"],
                    "filename": file_metadata["original_name"],
                    "size": file_metadata["size"],
                    "status": "uploaded"
                })
                logger.info(f"Successfully uploaded file: {file.filename}")

            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {e}")
                errors.append(f"{file.filename}: {str(e)}")

        return {
            "success": len(uploaded_files) > 0,
            "message": f"Successfully uploaded {len(uploaded_files)} file(s)" + 
                      (f", {len(errors)} failed" if errors else ""),
            "files": uploaded_files,
            "errors": errors
        }

    def process_file(self, file_id: str, columns_to_keep: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process an uploaded file through the import pipeline.
        
        Args:
            file_id: Unique identifier for the uploaded file
            columns_to_keep: Optional list of columns to keep during processing
            
        Returns:
            Dict containing processing results
        """
        try:
            # Validate file exists
            file_info = self.file_manager.get_file_info(file_id)
            if not file_info:
                return {"success": False, "message": "File not found"}

            if file_info.get("status") == "processed":
                return {"success": True, "message": "File already processed", "rows_processed": 0}

            file_path = self.file_manager.get_file_path(file_id)
            if not file_path:
                return {"success": False, "message": "File not accessible"}

            # Update status to processing
            self.file_manager.update_file_status(file_id, "processing", progress=0)

            # Process using XLSXImporter
            importer = XLSXImporter(str(file_path), columns_to_keep=columns_to_keep)
            
            # Update progress
            self.file_manager.update_file_status(file_id, "processing", progress=50)
            
            # Process the file
            importer.process()
            
            # Move to processed directory
            processed_path = self.file_manager.move_to_processed(file_id)
            if not processed_path:
                self.file_manager.update_file_status(
                    file_id, "error", error="Failed to move to processed directory"
                )
                return {"success": False, "message": "Processing failed"}

            rows_processed = len(importer.rows) if hasattr(importer, "rows") else 0
            self.file_manager.update_file_status(
                file_id, "processed", progress=100, processed_rows=rows_processed
            )

            return {
                "success": True,
                "message": f"Successfully processed {file_info.get('original_name', 'file')}",
                "rows_processed": rows_processed
            }

        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}")
            self.file_manager.update_file_status(file_id, "error", error=str(e))
            return {"success": False, "message": f"Processing failed: {str(e)}"}

    def remove_duplicates(self, file_id: str, mode: str = "forceful") -> Dict[str, Any]:
        """
        Remove duplicates from a processed file.
        
        Args:
            file_id: Unique identifier for the processed file
            mode: "forceful" or "soft" deduplication mode
            
        Returns:
            Dict containing deduplication results
        """
        try:
            file_info = self.file_manager.get_file_info(file_id)
            if not file_info:
                return {"success": False, "message": "File not found"}

            if file_info.get("status") not in ["processed", "deduplicated"]:
                return {"success": False, "message": "File not processed yet"}

            if file_info.get("status") == "deduplicated":
                return {"success": True, "message": "Duplicates already removed"}

            file_path = self.file_manager.get_file_path(file_id)
            if not file_path:
                return {"success": False, "message": "File not accessible"}

            # Create importer instance and remove duplicates
            importer = XLSXImporter(str(file_path))
            importer.remove_duplicates(mode=mode)

            # Update file status
            self.file_manager.update_file_status(file_id, "deduplicated")

            return {
                "success": True,
                "message": "Successfully removed duplicates"
                # Note: XLSXImporter doesn't return count, could be enhanced
            }

        except Exception as e:
            logger.error(f"Error removing duplicates for {file_id}: {e}")
            return {"success": False, "message": f"Deduplication failed: {str(e)}"}

    def export_file(self, file_id: str, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export a processed file to XLSX format.
        
        Args:
            file_id: Unique identifier for the processed file
            columns: Optional list of specific columns to export
            
        Returns:
            Dict containing export results and download path
        """
        try:
            file_info = self.file_manager.get_file_info(file_id)
            if not file_info:
                return {"success": False, "message": "File not found"}

            if file_info.get("status") not in ["processed", "deduplicated", "exported"]:
                return {"success": False, "message": "File not processed yet"}

            file_path = self.file_manager.get_file_path(file_id)
            if not file_path:
                return {"success": False, "message": "File not accessible"}

            # Create export filename
            original_name = file_info.get("original_name", "export.xlsx")
            export_filename = f"processed_{original_name}"

            # Create download copy
            download_path = self.file_manager.create_download_copy(file_id, export_filename)
            if not download_path:
                return {"success": False, "message": "Failed to create download file"}

            # Export to the download path
            importer = XLSXImporter(str(file_path))
            importer.export_to_xlsx(str(download_path), columns=columns)

            # Update status
            self.file_manager.update_file_status(file_id, "exported")

            return {
                "success": True,
                "message": f"Successfully exported {original_name}",
                "download_path": str(download_path),
                "download_filename": export_filename
            }

        except Exception as e:
            logger.error(f"Error exporting file {file_id}: {e}")
            return {"success": False, "message": f"Export failed: {str(e)}"}

    def get_file_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a file.
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Dict containing complete file status information
        """
        try:
            file_info = self.file_manager.get_file_info(file_id)
            if not file_info:
                return {"success": False, "message": "File not found"}

            status = file_info.get("status", "unknown")
            return {
                "success": True,
                "file_info": {
                    "id": file_id,
                    "original_name": file_info.get("original_name"),
                    "filename": file_info.get("filename"),
                    "size": file_info.get("size", 0),
                    "status": status
                },
                "processed": status in ["processed", "deduplicated", "exported"],
                "duplicates_removed": status in ["deduplicated", "exported"],
                "exported": status == "exported",
                "download_url": f"/api/download/{file_id}" if status == "exported" else None,
                "error": file_info.get("error"),
                "progress": file_info.get("progress", 0),
                "processed_rows": file_info.get("processed_rows", 0)
            }

        except Exception as e:
            logger.error(f"Error getting status for {file_id}: {e}")
            return {"success": False, "message": "Failed to get status"}

    def get_all_files_status(self) -> Dict[str, Any]:
        """
        Get status information for all managed files.
        
        Returns:
            Dict containing status for all files
        """
        try:
            files_status = {}
            for file_id, file_info in self.file_manager.active_files.items():
                if not file_id.startswith("download_"):  # Skip temporary download files
                    status = file_info.get("status", "unknown")
                    files_status[file_id] = {
                        "file_info": {
                            "id": file_id,
                            "original_name": file_info.get("original_name"),
                            "filename": file_info.get("filename"),
                            "size": file_info.get("size", 0),
                            "status": status
                        },
                        "processed": status in ["processed", "deduplicated", "exported"],
                        "duplicates_removed": status in ["deduplicated", "exported"],
                        "exported": status == "exported",
                        "download_url": f"/api/download/{file_id}" if status == "exported" else None,
                        "error": file_info.get("error")
                    }

            return {"success": True, "files": files_status}

        except Exception as e:
            logger.error(f"Error getting all files status: {e}")
            return {"success": False, "message": "Failed to get status"}

    def cleanup_file(self, file_id: str) -> Dict[str, Any]:
        """
        Clean up a file and its associated metadata.
        
        Args:
            file_id: Unique identifier for the file to clean up
            
        Returns:
            Dict containing cleanup results
        """
        try:
            success = self.file_manager.cleanup_file(file_id)
            if success:
                return {"success": True, "message": "File cleaned up successfully"}
            else:
                return {"success": False, "message": "File not found"}

        except Exception as e:
            logger.error(f"Error cleaning up file {file_id}: {e}")
            return {"success": False, "message": "Cleanup failed"}

    def process_workflow(self, files: List[Any], columns_to_keep: Optional[List[str]] = None, 
                        remove_duplicates: bool = True, 
                        export_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute the complete import workflow for multiple files.
        
        This method combines upload, process, deduplicate, and export steps
        for a simplified API that reduces client-side complexity.
        
        Args:
            files: List of files to process
            columns_to_keep: Optional columns to keep during processing
            remove_duplicates: Whether to remove duplicates
            export_columns: Optional columns for export
            
        Returns:
            Dict containing workflow results
        """
        try:
            # Step 1: Upload files
            upload_result = self.upload_files(files)
            if not upload_result["success"]:
                return upload_result

            processed_files = []
            errors = []

            # Step 2: Process each file
            for file_info in upload_result["files"]:
                file_id = file_info["file_id"]
                
                # Process file
                process_result = self.process_file(file_id, columns_to_keep)
                if not process_result["success"]:
                    errors.append(f"{file_info['filename']}: {process_result['message']}")
                    continue

                # Remove duplicates if requested
                if remove_duplicates:
                    dedup_result = self.remove_duplicates(file_id)
                    if not dedup_result["success"]:
                        logger.warning(f"Failed to remove duplicates for {file_info['filename']}: {dedup_result['message']}")

                # Export file
                export_result = self.export_file(file_id, export_columns)
                if export_result["success"]:
                    processed_files.append({
                        "file_id": file_id,
                        "filename": file_info["filename"],
                        "rows_processed": process_result.get("rows_processed", 0),
                        "download_url": f"/api/download/{file_id}"
                    })
                else:
                    errors.append(f"{file_info['filename']}: {export_result['message']}")

            return {
                "success": len(processed_files) > 0,
                "message": f"Successfully processed {len(processed_files)} file(s)" + 
                          (f", {len(errors)} failed" if errors else ""),
                "processed_files": processed_files,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error in process_workflow: {e}")
            return {"success": False, "message": f"Workflow failed: {str(e)}"}


# Create a singleton instance for use in routes
importer_service = ImporterService()
