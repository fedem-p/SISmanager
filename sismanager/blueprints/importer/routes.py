"""
Routes for importer blueprint in SISmanager.
"""

from flask import Blueprint, render_template
from flask import request, redirect, url_for, send_from_directory, flash
import os
import uuid
from sismanager.services.inout.xlsx_importer_service import XLSXImporter
from sismanager.services.inout.backup_service import BackupManager

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)

ALLOWED_EXTENSIONS = {"xlsx", "xls"}

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
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)
    if not allowed_file(file.filename):
        flash("File type not allowed")
        return redirect(request.url)

    # Save uploaded file
    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data", "uploads"))
    os.makedirs(uploads_dir, exist_ok=True)
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}_{file.filename}"
    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)

    # Process XLSX, pass original filename for orderCode
    importer = XLSXImporter(file_path, original_filename=file.filename)
    importer.process()

    # Delete backups older than 30 days
    backup_manager = BackupManager()
    backup_manager.delete_old_backups(days=30)

    # Remove duplicates if checkbox checked
    remove_duplicates = request.form.get("remove_duplicates") == "yes"
    if remove_duplicates:
        importer.remove_duplicates(mode="forceful")

    # Export processed file
    processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data", "processed"))
    os.makedirs(processed_dir, exist_ok=True)
    output_filename = f"processed_{unique_id}.xlsx"
    output_path = os.path.join(processed_dir, output_filename)
    importer.export_to_xlsx(output_path)

    # Generate preview HTML (full table, scrollable in frontend)
    import pandas as pd
    df = pd.read_excel(output_path)
    output_preview = df.to_html(classes="table table-bordered", index=False)

    # Provide download link and preview
    return render_template(
        "importer/importer.html",
        download_link=url_for("importer.download_file", file_id=output_filename),
        output_preview=output_preview,
    )

@importer_bp.route("/api/download/<file_id>")
def download_file(file_id: str):
    """Download a processed file."""
    processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data", "processed"))
    return send_from_directory(processed_dir, file_id, as_attachment=True)
    pass

