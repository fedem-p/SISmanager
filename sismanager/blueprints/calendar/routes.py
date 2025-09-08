"""
Routes for calendar blueprint in SISmanager.
"""

from flask import Blueprint, render_template

calendar_bp = Blueprint(
    "calendar", __name__, template_folder="../../templates/calendar"
)


@calendar_bp.route("/calendar")
def calendar():
    """Render the calendar page."""
    return render_template("calendar/calendar.html")
