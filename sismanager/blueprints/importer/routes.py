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

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)

# Configuration
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
ALLOWED_EXTENSIONS = {"xlsx", "xls"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory storage for processing status (in production, use Redis or database)
processing_status: Dict[str, Dict[str, Any]] = {}


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@importer_bp.route("/importer")
def importer():
    """Render the importer page."""
    return render_template("importer/importer.html")


@importer_bp.route("/api/upload", methods=["POST"])
def upload_files():
    """Handle file uploads."""
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            return jsonify({"error": "No files selected"}), 400

        uploaded_files = []
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                # Generate unique filename to avoid conflicts
                original_filename = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())
                filename = f"{unique_id}_{original_filename}"
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                
                # Check file size
                file.seek(0, 2)  # Seek to end to get size
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > MAX_FILE_SIZE:
                    return jsonify({
                        "error": f"File {original_filename} is too large. Maximum size is 16MB."
                    }), 400
                
                # Save file
                file.save(file_path)
                
                # Store file info
                file_info = {
                    "id": unique_id,
                    "original_name": original_filename,
                    "filename": filename,
                    "file_path": file_path,
                    "size": file_size,
                    "status": "uploaded"
                }
                uploaded_files.append(file_info)
                
                # Initialize processing status
                processing_status[unique_id] = {
                    "file_info": file_info,
                    "processed": False,
                    "duplicates_removed": False,
                    "exported": False,
                    "importer": None,
                    "error": None
                }
                
                logger.info(f"Uploaded file: {original_filename} as {filename}")
            else:
                return jsonify({
                    "error": f"File type not allowed. Only .xlsx and .xls files are supported."
                }), 400

        return jsonify({
            "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
            "files": uploaded_files
        }), 200

    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


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
