from flask import Blueprint
from flask_restful import Api
from .resources import LoginAPI, LogoutAPI, UserAPI

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
api = Api(auth_bp)

def init_auth():
    # Register API resources
    api.add_resource(LoginAPI, '/api/login')
    api.add_resource(LogoutAPI, '/api/logout')
    api.add_resource(UserAPI, '/api/users')

    # Import routes after Blueprint creation
    from . import routes
    
    return auth_bp