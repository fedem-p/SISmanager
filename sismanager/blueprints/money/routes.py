"""
Routes for money blueprint in SISmanager.
"""

from flask import Blueprint, render_template

money_bp = Blueprint("money", __name__, template_folder="../../templates/money")


@money_bp.route("/money")
def money():
    """Render the money page."""
    return render_template("money/money.html")
