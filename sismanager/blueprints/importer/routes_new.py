"""
Routes for importer blueprint in SISmanager.
"""

from flask import Blueprint, render_template, request, jsonify, send_file
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


@importer_bp.route("/api/upload", methods=["POST"])
def upload_files():
    """Upload XLSX files for processing."""
    try:
        if "files" not in request.files:
            return jsonify({"success": False, "message": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            return jsonify({"success": False, "message": "No files selected"}), 400

        uploaded_files = []
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
                # Store file securely using FileManager
                file_metadata = file_manager.store_uploaded_file(file, file.filename)
                uploaded_files.append({
                    "file_id": file_metadata["id"],
                    "success": True,
                    **file_metadata
                })
                logger.info(f"Successfully uploaded file: {file.filename}")

            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {e}")
                errors.append(f"{file.filename}: Upload failed - {str(e)}")

        # Prepare response
        response_data = {
            "success": len(uploaded_files) > 0,
            "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
            "files": uploaded_files
        }

        if errors:
            response_data["errors"] = errors
            response_data["message"] += f", {len(errors)} failed"

        status_code = 200 if uploaded_files else 400
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Error in upload_files: {e}")
        return jsonify({"success": False, "message": "Upload failed"}), 500


@importer_bp.route("/api/process/<file_id>", methods=["POST"])
def process_file(file_id: str):
    """Process an uploaded XLSX file."""
    try:
        # Get file info from FileManager
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({"success": False, "message": "File not found"}), 404

        file_path = file_manager.get_file_path(file_id)
        if not file_path:
            return jsonify({"success": False, "message": "File not accessible"}), 404

        # Update status to processing
        file_manager.update_file_status(file_id, "processing", progress=0)

        # Process using XLSXImporter
        columns_to_keep = request.json.get("columns_to_keep") if request.json else None
        importer = XLSXImporter(str(file_path), columns_to_keep=columns_to_keep)
        
        # Update progress
        file_manager.update_file_status(file_id, "processing", progress=50)
        
        # Process the file
        importer.process()
        
        # Move to processed directory
        processed_path = file_manager.move_to_processed(file_id)
        if processed_path:
            file_manager.update_file_status(file_id, "processed", progress=100, 
                                          processed_rows=len(importer.rows) if hasattr(importer, 'rows') else 0)
        else:
            file_manager.update_file_status(file_id, "error", 
                                          error="Failed to move to processed directory")
            return jsonify({"success": False, "message": "Processing failed"}), 500

        return jsonify({
            "success": True,
            "message": "File processed successfully",
            "file_id": file_id,
            "processed_rows": len(importer.rows) if hasattr(importer, 'rows') else 0
        })

    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        file_manager.update_file_status(file_id, "error", error=str(e))
        return jsonify({"success": False, "message": f"Processing failed: {str(e)}"}), 500


@importer_bp.route("/api/remove-duplicates/<file_id>", methods=["POST"])
def remove_duplicates(file_id: str):
    """Remove duplicates from processed data."""
    try:
        # Get file info
        file_info = file_manager.get_file_info(file_id)
        if not file_info or file_info["status"] != "processed":
            return jsonify({"success": False, "message": "File not found or not processed"}), 404

        file_path = file_manager.get_file_path(file_id)
        if not file_path:
            return jsonify({"success": False, "message": "File not accessible"}), 404

        # Get mode from request
        mode = request.json.get("mode", "soft") if request.json else "soft"
        
        # Create importer instance and remove duplicates
        importer = XLSXImporter(str(file_path))
        importer.remove_duplicates(mode=mode)

        # Update file status
        file_manager.update_file_status(file_id, "deduplicated")

        return jsonify({
            "success": True,
            "message": "Duplicates removed successfully",
            "removed_count": 0  # XLSXImporter doesn't return count, could be enhanced
        })

    except Exception as e:
        logger.error(f"Error removing duplicates for {file_id}: {e}")
        return jsonify({"success": False, "message": f"Deduplication failed: {str(e)}"}), 500


@importer_bp.route("/api/export/<file_id>", methods=["POST"])
def export_file(file_id: str):
    """Export processed file to XLSX."""
    try:
        # Get file info
        file_info = file_manager.get_file_info(file_id)
        if not file_info or file_info["status"] not in ["processed", "deduplicated"]:
            return jsonify({"success": False, "message": "File not found or not processed"}), 404

        file_path = file_manager.get_file_path(file_id)
        if not file_path:
            return jsonify({"success": False, "message": "File not accessible"}), 404

        # Get columns from request
        columns = request.json.get("columns") if request.json else None
        
        # Create export filename
        original_name = file_info.get("original_name", "export")
        export_filename = f"processed_{original_name}"

        # Create importer instance and export
        importer = XLSXImporter(str(file_path))
        
        # Create download copy
        download_path = file_manager.create_download_copy(file_id, export_filename)
        if not download_path:
            return jsonify({"success": False, "message": "Failed to create download file"}), 500

        # Export to the download path
        importer.export_to_xlsx(str(download_path), columns=columns)

        return send_file(
            str(download_path),
            as_attachment=True,
            download_name=export_filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"Error exporting file {file_id}: {e}")
        return jsonify({"success": False, "message": f"Export failed: {str(e)}"}), 500


@importer_bp.route("/api/download/<file_id>", methods=["GET"])
def download_file(file_id: str):
    """Download a processed file."""
    try:
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({"success": False, "message": "File not found"}), 404

        file_path = file_manager.get_file_path(file_id)
        if not file_path:
            return jsonify({"success": False, "message": "File not accessible"}), 404

        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_info.get("original_name", "download.xlsx"),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({"success": False, "message": f"Download failed: {str(e)}"}), 500


@importer_bp.route("/api/status/<file_id>", methods=["GET"])
def get_file_status(file_id: str):
    """Get status of a specific file."""
    try:
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({"success": False, "message": "File not found"}), 404

        return jsonify({
            "success": True,
            "file_id": file_id,
            "status": file_info.get("status", "unknown"),
            "progress": file_info.get("progress", 0),
            "error": file_info.get("error"),
            "processed_rows": file_info.get("processed_rows", 0),
            "filename": file_info.get("original_name"),
            "size": file_info.get("size", 0)
        })

    except Exception as e:
        logger.error(f"Error getting status for {file_id}: {e}")
        return jsonify({"success": False, "message": "Failed to get status"}), 500


@importer_bp.route("/api/status", methods=["GET"])
def get_all_files_status():
    """Get status of all files."""
    try:
        # Get stats from file manager
        stats = file_manager.get_file_stats()
        
        # Get individual file statuses
        files_status = {}
        for file_id, file_info in file_manager.active_files.items():
            if not file_id.startswith('download_'):  # Skip temporary download files
                files_status[file_id] = {
                    "status": file_info.get("status", "unknown"),
                    "progress": file_info.get("progress", 0),
                    "filename": file_info.get("original_name"),
                    "error": file_info.get("error")
                }

        return jsonify({
            "success": True,
            "files": files_status,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error getting all files status: {e}")
        return jsonify({"success": False, "message": "Failed to get status"}), 500


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
