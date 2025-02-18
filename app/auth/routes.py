from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import mongo, login_manager
from .models import User
from .forms import LoginForm
from bson.objectid import ObjectId
from . import auth_bp


@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None
    except:
        return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'module_lead':
            return redirect(url_for('module_lead.dashboard'))
    
    form = LoginForm()
    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    response = redirect(url_for("auth.login"))
    logout_user()
    flash("You have been logged out.", "info")
    return response
