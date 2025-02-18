from flask_restful import Resource, reqparse
from flask import jsonify, request, url_for, redirect
from flask_login import login_user, logout_user, current_user, login_required
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash

class LoginAPI(Resource):
    def post(self):
        try:
            data = request.get_json()
            
            if not data:
                return {"success": False, "message": "No data provided"}, 400

            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return {"success": False, "message": "Email and password are required"}, 400

            user = User.find_by_email(email)
            
            if user and user.check_password(password):  # Changed from check_password_hash
                if not user.is_active:
                    return {"success": False, "message": "Your account is inactive. Please contact administrator."}, 401

                if user.role not in ["admin", "module_lead"]:
                    return {"success": False, "message": "You don't have permission to access this area."}, 403

                login_user(user, remember=True)  # Flask-Login handles session
                redirect_url = url_for('admin.dashboard') if user.role == "admin" else url_for('module_lead.dashboard')

                return {
                    "success": True,
                    "message": "Login successful",
                    "redirect_url": redirect_url,
                    "role": user.role
                }, 200

            return {"success": False, "message": "Invalid email or password"}, 401

        except Exception as e:
            print("Login API error:", str(e))
            return {"success": False, "message": "An error occurred during login"}, 500

class LogoutAPI(Resource):
    @login_required
    def post(self):
        logout_user()
        return {"message": "Logout successful"}, 200

class UserAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('username', type=str, required=True)
        self.reqparse.add_argument('email', type=str, required=True)
        self.reqparse.add_argument('password', type=str, required=True)
        self.reqparse.add_argument('role', type=str, required=True)
        super(UserAPI, self).__init__()

    @login_required
    def post(self):
        if current_user.role != 'admin':
            return {'message': 'Unauthorized'}, 403

        args = self.reqparse.parse_args()
        if User.find_by_email(args['email']):
            return {'message': 'Email already registered'}, 400

        try:
            user_data = {
                'username': args['username'],
                'email': args['email'],
                'password': generate_password_hash(args['password']),
                'role': args['role'],
                'is_active': True
            }
            result = User.create_user(user_data)
            return {'message': 'User created successfully', 'user_id': str(result.inserted_id)}, 201
        except Exception as e:
            return {'message': 'Error creating user', 'error': str(e)}, 500
