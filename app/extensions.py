from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_moment import Moment
from flask_cors import CORS
from flask_mail import Mail

mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
jwt = JWTManager()
moment = Moment()
cors = CORS()
mail = Mail()
