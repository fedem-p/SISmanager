"""
Routes for importer blueprint in SISmanager.
"""

import os
import uuid
from typing import Dict, Any
from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from sismanager.config import logger, DATA_DIR
from sismanager.services.inout.xlsx_importer_service import XLSXImporter
from sismanager.services.inout.backup_service import BackupManager
from sismanager.services.file_manager import file_manager

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)

# Configuration
ALLOWED_EXTENSIONS = {"xlsx", "xls"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
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
                uploaded_files.append(file_metadata)
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
    """Process an uploaded file."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        file_info = status["file_info"]
        
        if status["processed"]:
            return jsonify({"message": "File already processed"}), 200

        # Get optional columns to keep from request
        columns_to_keep = request.json.get("columns_to_keep") if request.json else None
        
        # Create XLSXImporter instance
        importer = XLSXImporter(
            xlsx_path=file_info["file_path"],
            columns_to_keep=columns_to_keep
        )
        
        # Process the file
        importer.process()
        
        # Update status
        status["processed"] = True
        status["importer"] = importer  # Keep reference for later operations
        status["error"] = None
        
        logger.info(f"Processed file: {file_info['original_name']}")
        
        return jsonify({
            "message": f"Successfully processed {file_info['original_name']}",
            "rows_processed": len(importer.rows)
        }), 200

    except Exception as e:
        logger.error(f"Error processing file {file_id}: {str(e)}")
        if file_id in processing_status:
            processing_status[file_id]["error"] = str(e)
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/remove-duplicates/<file_id>", methods=["POST"])
def remove_duplicates(file_id: str):
    """Remove duplicates for a processed file."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        
        if not status["processed"]:
            return jsonify({"error": "File must be processed first"}), 400
            
        if status["duplicates_removed"]:
            return jsonify({"message": "Duplicates already removed"}), 200

        importer = status["importer"]
        if not importer:
            return jsonify({"error": "No importer instance found"}), 500

        # Get mode from request (default to 'forceful')
        mode = request.json.get("mode", "forceful") if request.json else "forceful"
        
        # Remove duplicates
        importer.remove_duplicates(mode=mode)
        
        # Update status
        status["duplicates_removed"] = True
        status["error"] = None
        
        logger.info(f"Removed duplicates from file: {status['file_info']['original_name']}")
        
        return jsonify({
            "message": "Successfully removed duplicates"
        }), 200

    except Exception as e:
        logger.error(f"Error removing duplicates for file {file_id}: {str(e)}")
        if file_id in processing_status:
            processing_status[file_id]["error"] = str(e)
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/export/<file_id>", methods=["POST"])
def export_file(file_id: str):
    """Export processed file to XLSX."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        
        if not status["processed"]:
            return jsonify({"error": "File must be processed first"}), 400

        importer = status["importer"]
        if not importer:
            return jsonify({"error": "No importer instance found"}), 500

        # Get export parameters from request
        export_params = request.json or {}
        columns = export_params.get("columns", ["orderCode", "idOrderPos", "descrizioneMateriale", "codiceMateriale"])
        
        # Create output filename
        original_name = status["file_info"]["original_name"]
        output_filename = f"exported_{original_name}"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        
        # Export to XLSX
        importer.export_to_xlsx(output_path, columns=columns)
        
        # Update status
        status["exported"] = True
        status["export_path"] = output_path
        status["export_filename"] = output_filename
        status["error"] = None
        
        logger.info(f"Exported file: {original_name} to {output_filename}")
        
        return jsonify({
            "message": f"Successfully exported {original_name}",
            "download_url": f"/api/download/{file_id}"
        }), 200

    except Exception as e:
        logger.error(f"Error exporting file {file_id}: {str(e)}")
        if file_id in processing_status:
            processing_status[file_id]["error"] = str(e)
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/download/<file_id>", methods=["GET"])
def download_file(file_id: str):
    """Download exported file."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        
        if not status["exported"] or "export_path" not in status:
            return jsonify({"error": "File not exported yet"}), 400

        export_path = status["export_path"]
        export_filename = status["export_filename"]
        
        if not os.path.exists(export_path):
            return jsonify({"error": "Export file not found"}), 404

        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/status/<file_id>", methods=["GET"])
def get_file_status(file_id: str):
    """Get processing status of a file."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        
        # Return status without the importer object (not JSON serializable)
        response_status = {
            "file_info": status["file_info"],
            "processed": status["processed"],
            "duplicates_removed": status["duplicates_removed"],
            "exported": status["exported"],
            "error": status["error"]
        }
        
        if status["exported"] and "export_filename" in status:
            response_status["download_url"] = f"/api/download/{file_id}"
        
        return jsonify(response_status), 200

    except Exception as e:
        logger.error(f"Error getting status for file {file_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/status", methods=["GET"])
def get_all_files_status():
    """Get status of all uploaded files."""
    try:
        all_status = {}
        
        for file_id, status in processing_status.items():
            response_status = {
                "file_info": status["file_info"],
                "processed": status["processed"],
                "duplicates_removed": status["duplicates_removed"],
                "exported": status["exported"],
                "error": status["error"]
            }
            
            if status["exported"] and "export_filename" in status:
                response_status["download_url"] = f"/api/download/{file_id}"
            
            all_status[file_id] = response_status
        
        return jsonify(all_status), 200

    except Exception as e:
        logger.error(f"Error getting all files status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@importer_bp.route("/api/cleanup/<file_id>", methods=["DELETE"])
def cleanup_file(file_id: str):
    """Clean up uploaded and exported files."""
    try:
        if file_id not in processing_status:
            return jsonify({"error": "File not found"}), 404

        status = processing_status[file_id]
        file_info = status["file_info"]
        
        # Remove uploaded file
        if os.path.exists(file_info["file_path"]):
            os.remove(file_info["file_path"])
            logger.info(f"Removed uploaded file: {file_info['filename']}")
        
        # Remove exported file if exists
        if "export_path" in status and os.path.exists(status["export_path"]):
            os.remove(status["export_path"])
            logger.info(f"Removed exported file: {status['export_filename']}")
        
        # Remove from processing status
        del processing_status[file_id]
        
        return jsonify({"message": "File cleaned up successfully"}), 200

    except Exception as e:
        logger.error(f"Error cleaning up file {file_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
