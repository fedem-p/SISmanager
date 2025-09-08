"""
SISmanager Flask application factory.
"""

from flask import Flask

# Import and register blueprints
from sismanager.blueprints.main.routes import main_bp
from sismanager.blueprints.importer.routes import importer_bp
from sismanager.blueprints.calendar.routes import calendar_bp
from sismanager.blueprints.materials.routes import materials_bp
from sismanager.blueprints.money.routes import money_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configuration for file uploads
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_EXTENSIONS'] = ['.xlsx', '.xls']

    app.register_blueprint(main_bp)
    app.register_blueprint(importer_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(money_bp)

    return app
