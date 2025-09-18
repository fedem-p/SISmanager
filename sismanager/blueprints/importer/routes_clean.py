"""
Simplified routes for importer blueprint in SISmanager.

This version leverages the existing XLSXImporter, FileManager, and other services
to provide a clean, server-driven interface with minimal client-side complexity.
"""

import os
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

from sismanager.config import logger
from sismanager.services.inout.xlsx_importer_service import XLSXImporter
from sismanager.services.file_manager import file_manager

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)

# Configuration
ALLOWED_EXTENSIONS = {"xlsx", "xls"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB


def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@importer_bp.route("/importer")
def importer():
    """Render the importer page."""
    return render_template("importer/importer.html")


@importer_bp.route("/importer/upload", methods=["POST"])
def upload_and_process():
    """
    Handle file upload and complete processing workflow.
    
    This single endpoint handles the entire workflow:
    1. Upload and validate files
    2. Process through XLSXImporter
    3. Optionally remove duplicates
    4. Provide download links
    
    This eliminates the need for complex client-side orchestration.
    """
    try:
        if "files" not in request.files:
            flash("No files provided", "error")
            return redirect(url_for("importer.importer"))

        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            flash("No files selected", "error")
            return redirect(url_for("importer.importer"))

        # Get processing options
        remove_duplicates = request.form.get("remove_duplicates") == "on"
        columns_to_keep = request.form.get("columns_to_keep")
        if columns_to_keep:
            columns_to_keep = [col.strip() for col in columns_to_keep.split(",") if col.strip()]
        else:
            columns_to_keep = None

        processed_files = []
        errors = []

        for file in files:
            if not file or file.filename == "":
                continue

            # Validate file
            if not allowed_file(file.filename):
                errors.append(f"{file.filename}: Invalid file type")
                continue

            if file.content_length and file.content_length > MAX_FILE_SIZE:
                errors.append(f"{file.filename}: File too large")
                continue

            try:
                # Store file using FileManager
                file_metadata = file_manager.store_uploaded_file(file, file.filename)
                file_path = file_manager.get_file_path(file_metadata["id"])
                
                if not file_path:
                    errors.append(f"{file.filename}: Failed to store file")
                    continue

                # Process using existing XLSXImporter - this handles the complete workflow!
                importer = XLSXImporter(str(file_path), columns_to_keep=columns_to_keep)
                importer.process()  # This already handles backup, read, and append to central DB
                
                rows_processed = len(importer.rows) if hasattr(importer, "rows") else 0
                
                # Remove duplicates if requested
                if remove_duplicates:
                    try:
                        importer.remove_duplicates(mode="forceful")
                        logger.info(f"Removed duplicates for {file.filename}")
                    except Exception as e:
                        logger.warning(f"Failed to remove duplicates for {file.filename}: {e}")

                # Create export file
                export_filename = f"processed_{file.filename}"
                export_path = file_manager.create_download_copy(file_metadata["id"], export_filename)
                
                if export_path:
                    # Export using existing method
                    export_columns = ["orderCode", "idOrderPos", "descrizioneMateriale", "codiceMateriale"]
                    importer.export_to_xlsx(str(export_path), columns=export_columns)
                    
                    processed_files.append({
                        "filename": file.filename,
                        "rows_processed": rows_processed,
                        "download_url": url_for("importer.download_file", file_id=file_metadata["id"]),
                        "file_id": file_metadata["id"]
                    })
                else:
                    errors.append(f"{file.filename}: Failed to create export file")

                # Update file status
                file_manager.update_file_status(file_metadata["id"], "processed")
                logger.info(f"Successfully processed {file.filename} with {rows_processed} rows")

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {e}")
                errors.append(f"{file.filename}: {str(e)}")

        # Provide user feedback
        if processed_files:
            flash(f"Successfully processed {len(processed_files)} file(s)", "success")
            if errors:
                flash(f"{len(errors)} file(s) failed to process", "warning")
        else:
            flash("No files were processed successfully", "error")
            
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, "error")

        return render_template("importer/results.html", 
                             processed_files=processed_files, 
                             errors=errors)

    except Exception as e:
        logger.error(f"Error in upload_and_process: {e}")
        flash(f"Processing failed: {str(e)}", "error")
        return redirect(url_for("importer.importer"))


@importer_bp.route("/importer/quick-process", methods=["POST"])
def quick_process():
    """
    Quick processing endpoint for AJAX requests.
    Processes files with default settings and returns JSON.
    """
    try:
        if "files" not in request.files:
            return jsonify({"success": False, "message": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            return jsonify({"success": False, "message": "No files selected"}), 400

        processed_count = 0
        total_rows = 0

        for file in files:
            if not file or file.filename == "":
                continue

            if not allowed_file(file.filename):
                continue

            try:
                # Store and process file
                file_metadata = file_manager.store_uploaded_file(file, file.filename)
                file_path = file_manager.get_file_path(file_metadata["id"])
                
                if file_path:
                    # Use existing XLSXImporter workflow
                    importer = XLSXImporter(str(file_path))
                    importer.process()
                    
                    processed_count += 1
                    total_rows += len(importer.rows) if hasattr(importer, "rows") else 0
                    
                    file_manager.update_file_status(file_metadata["id"], "processed")

            except Exception as e:
                logger.error(f"Error in quick processing {file.filename}: {e}")
                continue

        return jsonify({
            "success": processed_count > 0,
            "message": f"Processed {processed_count} file(s), {total_rows} total rows",
            "processed_count": processed_count,
            "total_rows": total_rows
        })

    except Exception as e:
        logger.error(f"Error in quick_process: {e}")
        return jsonify({"success": False, "message": "Processing failed"}), 500


@importer_bp.route("/api/download/<file_id>")
def download_file(file_id: str):
    """Download a processed file."""
    try:
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            flash("File not found", "error")
            return redirect(url_for("importer.importer"))

        file_path = file_manager.get_file_path(file_id)
        if not file_path:
            flash("File not accessible", "error")
            return redirect(url_for("importer.importer"))

        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_info.get("original_name", "processed_data.xlsx"),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        flash("Download failed", "error")
        return redirect(url_for("importer.importer"))


@importer_bp.route("/api/cleanup/<file_id>", methods=["DELETE"])
def cleanup_file(file_id: str):
    """Clean up a file and its metadata."""
    try:
        success = file_manager.cleanup_file(file_id)
        if success:
            return jsonify({"success": True, "message": "File cleaned up successfully"})
        else:
            return jsonify({"success": False, "message": "File not found"}), 404

    except Exception as e:
        logger.error(f"Error cleaning up file {file_id}: {e}")
        return jsonify({"success": False, "message": "Cleanup failed"}), 500


@importer_bp.route("/importer/status")
def status():
    """Show status of all files."""
    try:
        # Get file statistics from FileManager
        stats = file_manager.get_file_stats()
        
        # Get individual file information
        files_info = []
        for file_id, file_info in file_manager.active_files.items():
            if not file_id.startswith("download_"):  # Skip temporary download files
                files_info.append({
                    "id": file_id,
                    "filename": file_info.get("original_name", "Unknown"),
                    "status": file_info.get("status", "unknown"),
                    "size": file_info.get("size", 0),
                    "upload_time": file_info.get("upload_time"),
                    "processed_rows": file_info.get("processed_rows", 0),
                    "error": file_info.get("error")
                })

        return render_template("importer/status.html", files=files_info, stats=stats)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        flash("Failed to get status", "error")
        return redirect(url_for("importer.importer"))


# Keep minimal API endpoints for backward compatibility if needed
@importer_bp.route("/api/status")
def api_status():
    """API endpoint for getting all files status."""
    try:
        files_status = {}
        for file_id, file_info in file_manager.active_files.items():
            if not file_id.startswith("download_"):
                files_status[file_id] = {
                    "status": file_info.get("status", "unknown"),
                    "filename": file_info.get("original_name"),
                    "error": file_info.get("error"),
                }

        return jsonify({"success": True, "files": files_status})

    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return jsonify({"success": False, "message": "Failed to get status"}), 500
