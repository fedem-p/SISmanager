"""
Routes for calendar blueprint in SISmanager.
"""

from datetime import datetime, date
import calendar as cal
from flask import Blueprint, render_template, request

calendar_bp = Blueprint(
    "calendar", __name__, template_folder="../../templates/calendar"
)


@calendar_bp.route("/calendar")
def calendar():
    """Render the calendar page with month navigation."""
    # Get month and year from query parameters or default to current
    current_date = datetime.now()
    try:
        year = int(request.args.get("year", current_date.year))
        month = int(request.args.get("month", current_date.month))
    except (ValueError, TypeError):
        year = current_date.year
        month = current_date.month

    # Validate month and year ranges - maintain user intent where possible
    year_valid = 1900 <= year <= 2100
    month_valid = 1 <= month <= 12

    # If both invalid, reset to current date
    if not year_valid and not month_valid:
        year = current_date.year
        month = current_date.month
    # If only year invalid, keep user's month choice but use current year
    elif not year_valid:
        year = current_date.year
    # If only month invalid, keep user's year choice but use current month
    elif not month_valid:
        month = current_date.month

    # Get calendar data
    calendar_data = generate_calendar_data(year, month)

    return render_template("calendar/calendar.html", **calendar_data)


def generate_calendar_data(year: int, month: int) -> dict:
    """Generate calendar data for the given year and month."""
    # Create calendar instance
    cal_instance = cal.Calendar(firstweekday=0)  # Monday = 0

    # Get month calendar as a matrix of weeks
    month_calendar = cal_instance.monthdayscalendar(year, month)

    # Get month and year names
    month_name = cal.month_name[month]

    # Calculate previous and next month/year
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # Get current date for highlighting today
    today = date.today()
    is_current_month = year == today.year and month == today.month
    current_day = today.day if is_current_month else None

    # Day names for header
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "month_calendar": month_calendar,
        "day_names": day_names,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "current_day": current_day,
        "is_current_month": is_current_month,
    }
