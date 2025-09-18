"""
Simplified routes for importer blueprint in SISmanager.

This refactored version uses the ImporterService to handle business logic,
making routes thin and focused on HTTP concerns only.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file,
    flash,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename

from sismanager.config import logger
from sismanager.services.importer_service import importer_service

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)


@importer_bp.route("/importer")
def importer():
    """Render the importer page with current status."""
    try:
        # Get current status for server-side rendering
        status_result = importer_service.get_all_files_status()
        files_status = (
            status_result.get("files", {}) if status_result["success"] else {}
        )

        return render_template("importer/importer.html", files_status=files_status)
    except Exception as e:
        logger.error(f"Error loading importer page: {e}")
        flash("Error loading importer page", "error")
        return render_template("importer/importer.html", files_status={})


@importer_bp.route("/importer/upload", methods=["POST"])
def upload_files():
    """Handle file upload via form submission."""
    try:
        files = request.files.getlist("files")
        result = importer_service.upload_files(files)

        if result["success"]:
            flash(result["message"], "success")
            if result.get("errors"):
                for error in result["errors"]:
                    flash(error, "warning")
        else:
            flash(result["message"], "error")

        return redirect(url_for("importer.importer"))

    except Exception as e:
        logger.error(f"Error in upload_files: {e}")
        flash("Upload failed due to server error", "error")
        return redirect(url_for("importer.importer"))


@importer_bp.route("/importer/process-all", methods=["POST"])
def process_all_files():
    """Process all uploaded files using the complete workflow."""
    try:
        # Get options from form
        remove_duplicates = request.form.get("remove_duplicates") == "on"
        columns_to_keep = request.form.get("columns_to_keep")
        export_columns = request.form.get("export_columns")

        # Parse column lists if provided
        columns_to_keep_list = None
        if columns_to_keep:
            columns_to_keep_list = [
                col.strip() for col in columns_to_keep.split(",") if col.strip()
            ]

        export_columns_list = None
        if export_columns:
            export_columns_list = [
                col.strip() for col in export_columns.split(",") if col.strip()
            ]
        else:
            # Default export columns from documentation
            export_columns_list = [
                "orderCode",
                "idOrderPos",
                "descrizioneMateriale",
                "codiceMateriale",
            ]

        # Get all uploaded files that need processing
        status_result = importer_service.get_all_files_status()
        if not status_result["success"]:
            flash("Failed to get file status", "error")
            return redirect(url_for("importer.importer"))

        files_to_process = []
        for file_id, file_info in status_result["files"].items():
            if not file_info["processed"]:
                # We need to process files individually since workflow method expects file objects
                process_result = importer_service.process_file(
                    file_id, columns_to_keep_list
                )
                if process_result["success"]:
                    if remove_duplicates:
                        importer_service.remove_duplicates(file_id)
                    export_result = importer_service.export_file(
                        file_id, export_columns_list
                    )
                    if export_result["success"]:
                        files_to_process.append(file_info["file_info"]["original_name"])

        if files_to_process:
            flash(f"Successfully processed {len(files_to_process)} file(s)", "success")
        else:
            flash("No files were processed", "warning")

        return redirect(url_for("importer.importer"))

    except Exception as e:
        logger.error(f"Error in process_all_files: {e}")
        flash("Processing failed due to server error", "error")
        return redirect(url_for("importer.importer"))


@importer_bp.route("/importer/cleanup", methods=["POST"])
def cleanup_all_files():
    """Clean up all files."""
    try:
        status_result = importer_service.get_all_files_status()
        if status_result["success"]:
            cleaned_count = 0
            for file_id in status_result["files"].keys():
                cleanup_result = importer_service.cleanup_file(file_id)
                if cleanup_result["success"]:
                    cleaned_count += 1

            flash(f"Cleaned up {cleaned_count} file(s)", "success")
        else:
            flash("Failed to get file list for cleanup", "error")

        return redirect(url_for("importer.importer"))

    except Exception as e:
        logger.error(f"Error in cleanup_all_files: {e}")
        flash("Cleanup failed due to server error", "error")
        return redirect(url_for("importer.importer"))


# API Endpoints (Simplified for backward compatibility)


@importer_bp.route("/api/upload", methods=["POST"])
def api_upload_files():
    """API endpoint for file upload."""
    try:
        files = request.files.getlist("files")
        result = importer_service.upload_files(files)
        return jsonify(result), 200 if result["success"] else 400

    except Exception as e:
        logger.error(f"Error in api_upload_files: {e}")
        return jsonify({"success": False, "message": "Upload failed"}), 500


@importer_bp.route("/api/process/<file_id>", methods=["POST"])
def api_process_file(file_id: str):
    """API endpoint for processing a single file."""
    try:
        columns_to_keep = None
        if request.json:
            columns_to_keep = request.json.get("columns_to_keep")

        result = importer_service.process_file(file_id, columns_to_keep)
        return jsonify(result), (
            200
            if result["success"]
            else 404 if "not found" in result["message"].lower() else 500
        )

    except Exception as e:
        logger.error(f"Error in api_process_file: {e}")
        return jsonify({"success": False, "message": "Processing failed"}), 500


@importer_bp.route("/api/remove-duplicates/<file_id>", methods=["POST"])
def api_remove_duplicates(file_id: str):
    """API endpoint for removing duplicates."""
    try:
        mode = "forceful"
        if request.json:
            mode = request.json.get("mode", "forceful")

        result = importer_service.remove_duplicates(file_id, mode)
        status_code = 200
        if not result["success"]:
            if "not found" in result["message"].lower():
                status_code = 404
            elif "not processed" in result["message"].lower():
                status_code = 400
            else:
                status_code = 500

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error in api_remove_duplicates: {e}")
        return jsonify({"success": False, "message": "Deduplication failed"}), 500


@importer_bp.route("/api/export/<file_id>", methods=["POST"])
def api_export_file(file_id: str):
    """API endpoint for exporting a file."""
    try:
        columns = None
        if request.json:
            columns = request.json.get("columns")

        result = importer_service.export_file(file_id, columns)

        if result["success"]:
            # Return file directly for download
            return send_file(
                result["download_path"],
                as_attachment=True,
                download_name=result["download_filename"],
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            status_code = 404 if "not found" in result["message"].lower() else 500
            return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error in api_export_file: {e}")
        return jsonify({"success": False, "message": "Export failed"}), 500


@importer_bp.route("/api/download/<file_id>", methods=["GET"])
def api_download_file(file_id: str):
    """API endpoint for downloading an exported file."""
    try:
        status_result = importer_service.get_file_status(file_id)
        if not status_result["success"]:
            return jsonify({"success": False, "message": "File not found"}), 404

        if not status_result["exported"]:
            return jsonify({"success": False, "message": "File not exported yet"}), 400

        # Re-export to ensure fresh download
        export_result = importer_service.export_file(file_id)
        if export_result["success"]:
            return send_file(
                export_result["download_path"],
                as_attachment=True,
                download_name=export_result["download_filename"],
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            return jsonify(export_result), 500

    except Exception as e:
        logger.error(f"Error in api_download_file: {e}")
        return jsonify({"success": False, "message": "Download failed"}), 500


@importer_bp.route("/api/status/<file_id>", methods=["GET"])
def api_get_file_status(file_id: str):
    """API endpoint for getting file status."""
    try:
        result = importer_service.get_file_status(file_id)
        return jsonify(result), 200 if result["success"] else 404

    except Exception as e:
        logger.error(f"Error in api_get_file_status: {e}")
        return jsonify({"success": False, "message": "Failed to get status"}), 500


@importer_bp.route("/api/status", methods=["GET"])
def api_get_all_files_status():
    """API endpoint for getting all files status."""
    try:
        result = importer_service.get_all_files_status()
        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        logger.error(f"Error in api_get_all_files_status: {e}")
        return jsonify({"success": False, "message": "Failed to get status"}), 500


@importer_bp.route("/api/cleanup/<file_id>", methods=["DELETE"])
def api_cleanup_file(file_id: str):
    """API endpoint for cleaning up a file."""
    try:
        result = importer_service.cleanup_file(file_id)
        return jsonify(result), 200 if result["success"] else 404

    except Exception as e:
        logger.error(f"Error in api_cleanup_file: {e}")
        return jsonify({"success": False, "message": "Cleanup failed"}), 500
