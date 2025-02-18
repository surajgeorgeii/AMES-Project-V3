from flask import Blueprint, g
from flask_restful import Api
from flask_login import current_user

module_lead_bp = Blueprint('module_lead', __name__, url_prefix='/module-lead')  
api = Api(module_lead_bp) 

@module_lead_bp.before_request
def before_request():
    g.user = current_user

def init_module_lead():
    from .resources import UserResource, ModuleResource, ReviewResource, ModuleCodePrefixResource

    # Add resources with corrected paths (removed duplicate /module-lead prefix)
    api.add_resource(UserResource, '/api/users', '/api/users/<user_id>')
    api.add_resource(ModuleResource, '/api/modules', '/api/modules/<module_id>')
    api.add_resource(ReviewResource, '/api/reviews', '/api/reviews/<review_id>', '/api/reviews/module/<module_id>')
    api.add_resource(ModuleCodePrefixResource, "/api/modules/code_prefixes")

    from . import routes
    return module_lead_bp