import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
class Config:
    # Flask Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
    
    # API Settings
    API_BASE_URL = 'http://127.0.0.1:5000/api'

    # Mail Settings
    MAIL_SERVER = os.getenv("MAIL_SERVER", 'localhost')
    MAIL_PORT = os.getenv("MAIL_PORT", 1025)
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", None)
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", None)
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", 'no-reply@localhost')
    SYSTEM_URL = os.getenv("SYSTEM_URL", 'http://localhost:5000')
    
class DevelopmentConfig(Config):
    # Flask Settings
    FLASK_APP = os.getenv("FLASK_APP", "run.py")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    # Database Settings
    MONGO_URI = os.getenv("MONGO_URI")

    # Session Settings
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY= os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE= os.getenv("SESSION_COOKIE_SAMESITE", 'Lax')

config = {
    "development": DevelopmentConfig,
    "default": DevelopmentConfig
}