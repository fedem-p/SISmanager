"""
Routes for importer blueprint in SISmanager.
"""

from flask import Blueprint, render_template

importer_bp = Blueprint(
    "importer", __name__, template_folder="../../templates/importer"
)


@importer_bp.route("/importer")
def importer():
    """Render the importer page."""
    return render_template("importer/importer.html")
