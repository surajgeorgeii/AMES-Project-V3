from flask import Blueprint, g
from flask_restful import Api
from flask_login import current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
api = Api(admin_bp, prefix='/api')

@admin_bp.before_request
def before_request():
    g.user = current_user

def init_admin():
    from .resources import (UserResource, ModuleResource, ReviewResource, 
                            ModuleCodePrefixResource, ModuleReminderResource,
                            UserEmailResource)
    from .utils import ModuleUploadResource
    
    # Add resources without /api prefix since it's handled by Api instance
    api.add_resource(UserResource, '/users', '/users/<user_id>')
    api.add_resource(ModuleResource, '/modules', '/modules/<module_id>')
    api.add_resource(ReviewResource, '/reviews', '/reviews/<review_id>', '/reviews/module/<module_id>')
    api.add_resource(ModuleUploadResource, '/modules/upload')
    api.add_resource(ModuleCodePrefixResource, "/modules/code_prefixes")
    api.add_resource(ModuleReminderResource, '/api/admin/modules/send-reminders')
    api.add_resource(UserEmailResource, '/api/users/<user_id>/email')
    from . import routes  
    return admin_bp
