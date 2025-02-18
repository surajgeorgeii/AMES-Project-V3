from bson.objectid import ObjectId
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get("_id"))
        self.username = user_data["username"]
        self.password = user_data["password"]
        self.email = user_data["email"]
        self._is_active = user_data.get("is_active", True)
        self.role = user_data.get("role", "module_lead")

    @property
    def is_admin(self):
        return self.role == "admin"
    
    @property
    def is_module_lead(self):
        return self.role == "module_lead"

    @property
    def is_active(self):
        return self._is_active

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @staticmethod
    def find_by_email(email):
        user_data = mongo.db.users.find_one({"email": email})
        return User(user_data) if user_data else None

    @staticmethod
    def create_admin():
        admin_user = mongo.db.users.find_one({"role": "admin"})
        if not admin_user:
            mongo.db.users.insert_one({
                "username": "Admin User",
                "password": generate_password_hash("admin123"),
                "email": "admin@ames.edu.eu",
                "is_active": True,
                "role": "admin"
            })

    @staticmethod
    def create_user(user_data):
        return mongo.db.users.insert_one(user_data)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return self.id
