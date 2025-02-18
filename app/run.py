from flask import Flask, render_template
from config import config
from extensions import mongo, login_manager, jwt, moment, cors, mail
from auth import init_auth
from admin import init_admin
from module_lead import init_module_lead
from base.routes import base_bp
from auth.models import User
from base.utils import get_academic_year
from datetime import datetime

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config['development'])
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters and globals
    register_template_utilities(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    mongo.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    moment.init_app(app)
    cors.init_app(app)
    mail.init_app(app)

def register_blueprints(app):
    """Register Flask blueprints"""
    auth_bp = init_auth()
    admin_bp = init_admin()
    module_lead_bp = init_module_lead()
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(module_lead_bp)
    app.register_blueprint(base_bp)

def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

def register_template_utilities(app):
    """Register template filters and global variables"""
    def format_datetime(value):
        if isinstance(value, dict) and '$date' in value:
            try:
                dt = datetime.strptime(value['$date'], '%Y-%m-%dT%H:%M:%S.%fZ')
                return dt.strftime('%Y-%m-%d %H:%M UTC')
            except (ValueError, KeyError):
                return 'Invalid date'
        return value or 'No date recorded'

    # Register template filters
    app.jinja_env.filters['datetime'] = format_datetime
    
    # Register global variables
    app.jinja_env.globals.update(
        get_academic_year=get_academic_year,
        max=max,
        min=min
    )

def initialize_database(app):
    """Initialize database with required data"""
    with app.app_context():
        User.create_admin()

# Application initialization
app = create_app()
initialize_database(app)

if __name__ == "__main__":
    app.run(debug=True)
