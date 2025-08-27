from flask import Flask

def create_app():
    app = Flask(__name__)

    # Import and register blueprints
    from sismanager.blueprints.main.routes import main_bp
    from sismanager.blueprints.importer.routes import importer_bp
    from sismanager.blueprints.calendar.routes import calendar_bp
    from sismanager.blueprints.materials.routes import materials_bp
    from sismanager.blueprints.money.routes import money_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(importer_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(money_bp)

    return app
