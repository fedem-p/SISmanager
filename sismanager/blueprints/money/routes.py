from flask import Blueprint, render_template

money_bp = Blueprint('money', __name__, template_folder='../../templates/money')

@money_bp.route('/money')
def money():
    return render_template('money/money.html')
