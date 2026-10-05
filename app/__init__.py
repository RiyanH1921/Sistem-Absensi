import os
from flask import Flask
from app.config import Config
from app.extensions import db, bcrypt, jwt, cors

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.routes.auth import auth_bp, auth_views
    from app.routes.master import master_bp
    from app.routes.lesson import lesson_bp
    from app.routes.attendance import attendance_bp
    from app.routes.report import report_bp
    from app.routes.views import views_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_views)
    app.register_blueprint(master_bp)
    app.register_blueprint(lesson_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(views_bp)

    return app
