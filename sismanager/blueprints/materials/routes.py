from flask import Blueprint, render_template

materials_bp = Blueprint('materials', __name__, template_folder='../../templates/materials')

@materials_bp.route('/materials')
def materials():
    return render_template('materials/materials.html')
