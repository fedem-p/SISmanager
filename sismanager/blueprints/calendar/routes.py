from flask import Blueprint, render_template

calendar_bp = Blueprint('calendar', __name__, template_folder='../../templates/calendar')

@calendar_bp.route('/calendar')
def calendar():
    return render_template('calendar/calendar.html')
