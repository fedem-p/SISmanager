"""
Routes for materials blueprint in SISmanager.
"""

from flask import Blueprint, render_template

materials_bp = Blueprint(
    "materials", __name__, template_folder="../../templates/materials"
)


@materials_bp.route("/materials")
def materials():
    """Render the materials page."""
    return render_template("materials/materials.html")
