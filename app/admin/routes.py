import requests
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from . import admin_bp
from auth.utils import admin_required
from auth.forms import UserCreateForm
from .forms import UploadForm
from .constants import ENHANCEMENT_PLAN_OPTIONS
from datetime import datetime
from bson import ObjectId
from flask_wtf import FlaskForm
from base.utils import get_academic_year
import logging as logger
from .resources import ModuleReminderResource
from utils.email import send_custom_email  # Add this import at the top
from .resources import UserEmailResource

# API configuration
API_BASE_URL = "http://localhost:5000/admin/api"

def make_request(method, endpoint, **kwargs):
    """Helper function to make API requests with session cookies"""
    url = f"{API_BASE_URL}{endpoint}"
    cookies = {'session': session.get('_id')}
    kwargs.update({'cookies': cookies})
    
    try:
        response = requests.request(method, url, **kwargs)
        return response
    except Exception as e:
        print(f"API Request Error: {str(e)}")
        raise

def extract_object_id(id_str):
    """Helper function to extract ObjectId from various formats"""
    try:
        if not id_str:
            return None
            
        # If it's already an ObjectId, convert to string
        if isinstance(id_str, ObjectId):
            return str(id_str)
            
        # If it's a dict with $oid (MongoDB format)
        if isinstance(id_str, dict) and '$oid' in id_str:
            return str(id_str['$oid'])
            
        # If it's a string, clean and validate
        id_str = str(id_str).strip()
        if ObjectId.is_valid(id_str):
            return id_str
            
        return None
    except Exception as e:
        print(f"Error extracting ObjectId: {str(e)}")
        return None

# ------------------------------
# Admin Dashboard
# ------------------------------
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    current_academic_year = get_academic_year()
    
    stats = {
        "total_modules": 0,
        "pending_reviews": 0,
        "completed_reviews": 0,
        "total_users": 0,
        "admin_users": 0,
        "module_leads": 0,
        "academic_year": current_academic_year
    }
    
    try:
        # Get module counts with academic year filter
        response = make_request('GET', '/modules', params={
            "count_only": "true",
            "academic_year": current_academic_year
        })
        
        if response.status_code == 200:
            module_data = response.json()
            if module_data.get("success"):
                counts = module_data.get("data", {}).get("counts", {})
                stats.update({
                    "total_modules": counts.get("total", 0),
                    "pending_reviews": counts.get("pending", 0),
                    "completed_reviews": counts.get("completed", 0)
                })
        
        # Get user counts (users are not filtered by academic year)
        response_users = make_request('GET', '/users', params={"count_only": "true"})
        if response_users.status_code == 200:
            user_data = response_users.json()
            if user_data.get("success"):
                counts = user_data.get("data", {}).get("counts", {})
                stats.update({
                    "total_users": counts.get("total", 0),
                    "admin_users": counts.get("admin", 0),
                    "module_leads": counts.get("module_lead", 0)
                })

    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        flash(f"Error fetching dashboard data: {str(e)}", "danger")

    return render_template("admin/dashboard.html", stats=stats)


# ------------------------------
# User Management
# ------------------------------
@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def view_users():
    form = UserCreateForm()
    search_query = request.args.get("search", "")
    status_filter = request.args.get("status", "all")
    sort_by = request.args.get("sort", "username")
    sort_direction = request.args.get("direction", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    params = {
        "search": search_query,
        "page": page,
        "per_page": per_page,
        "sort": sort_by,
        "direction": sort_direction
    }
    
    # Add status filter to API params
    if status_filter == "active":
        params["is_active"] = True
    elif status_filter == "flagged":
        params["is_active"] = False
    
    response = make_request('GET', '/users', params=params)
    if response.status_code == 200:
        data = response.json().get('data', {})
        users = data.get('items', [])
        total_users = data.get('total', 0)
        total_pages = (total_users + per_page - 1) // per_page
    else:
        users = []
        total_users = 0
        total_pages = 1

    if form.validate_on_submit():
        data = {
            "username": form.username.data,
            "email": form.email.data,
            "password": form.password.data,
            "role": form.role.data,
        }
        res = make_request('POST', '/users', json=data)
        if res.status_code == 201:
            flash("User created successfully!", "success")
        else:
            flash("Error creating user", "danger")
        return redirect(url_for('admin.view_users'))

    return render_template(
        "admin/users.html",
        users=users,
        form=form,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_direction=sort_direction
    )


@admin_bp.route("/users/<user_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_user_status(user_id):
    try:
        print(f"Toggling status for user_id: {user_id}")  # Debug print
        
        # Clean the user ID first
        if isinstance(user_id, dict) and '$oid' in user_id:
            user_id = user_id['$oid']
        else:
            user_id = str(user_id)
        
        print(f"Cleaned user_id: {user_id}")  # Debug print
        
        # Get current user status
        response = make_request('GET', f'/users/{user_id}')
        print(f"GET Response: {response.status_code}")  # Debug print
        print(f"GET Response content: {response.text}")  # Debug print
        
        try:
            response_data = response.json()
        except ValueError as e:
            print(f"JSON decode error: {str(e)}")  # Debug print
            flash("Error: Invalid server response", "danger")
            return redirect(url_for('admin.view_users'))

        if not response_data or not response_data.get('success'):
            flash("Error: " + response_data.get('message', 'Failed to get user data'), "danger")
            return redirect(url_for('admin.view_users'))

        user_data = response_data.get('data')
        if not user_data:
            flash("Error: User data not found", "danger")
            return redirect(url_for('admin.view_users'))

        current_status = user_data.get('is_active', True)
        
        # Toggle the status
        update_data = {"is_active": not current_status}
        print(f"Sending update: {update_data}")  # Debug print
        
        update_response = make_request('PUT', f'/users/{user_id}', json=update_data)
        print(f"PUT Response: {update_response.status_code}")  # Debug print
        print(f"PUT Response content: {update_response.text}")  # Debug print
        
        try:
            update_result = update_response.json()
        except ValueError:
            flash("Error: Invalid response during update", "danger")
            return redirect(url_for('admin.view_users'))

        if update_response.status_code == 200 and update_result.get('success'):
            status_text = "unblocked" if not current_status else "blocked"
            flash(f"User has been {status_text} successfully", "success")
        else:
            error_msg = update_result.get('message', 'Failed to update user status')
            flash(f"Error: {error_msg}", "danger")
            
        return redirect(url_for('admin.view_users'))
        
    except Exception as e:
        print(f"Error in toggle_user_status: {str(e)}")  # Debug print
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin.view_users'))


@admin_bp.route("/users/create", methods=["POST"])
@login_required
@admin_required
def create_user():
    try:
        data = request.get_json()
        print(f"Received create user request with data: {data}")  # Debug print

        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided",
                "errors": {"general": "Missing form data"}
            }), 400

        # Validate required fields
        required_fields = ["username", "email", "password", "role"]
        missing_fields = {field: ["This field is required"] 
                         for field in required_fields 
                         if not data.get(field)}
        
        if missing_fields:
            return jsonify({
                "success": False,
                "message": "Missing required fields",
                "errors": missing_fields
            }), 400

        # Make API request
        response = make_request('POST', '/users', json=data)
        print(f"API response: {response.status_code}, {response.text}")  # Debug print

        try:
            result = response.json()
            if response.status_code == 201:
                return jsonify({
                    "success": True,
                    "message": "User created successfully"
                })

            return jsonify({
                "success": False,
                "message": result.get('message', 'Error creating user'),
                "errors": result.get('errors', {"general": ["Failed to create user"]})
            }), 400

        except ValueError as e:
            print(f"JSON decode error: {str(e)}")  # Debug print
            return jsonify({
                "success": False,
                "message": "Invalid server response",
                "errors": {"general": ["Server error occurred"]}
            }), 500

    except Exception as e:
        print(f"Error creating user: {str(e)}")  # Debug print
        return jsonify({
            "success": False,
            "message": "Server error occurred",
            "errors": {"general": [str(e)]}
        }), 500


@admin_bp.route("/users/<user_id>/send-email", methods=["POST"])
@login_required
@admin_required
def send_user_email(user_id):
    """Route handler for sending email to a user"""
    resource = UserEmailResource()
    return resource.post(user_id)


# ------------------------------
# Module Management
# ------------------------------
@admin_bp.route("/modules")
@login_required
@admin_required
def view_modules():
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    sort_by = request.args.get("sort", "module_code")
    sort_direction = request.args.get("direction", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    code_prefix = request.args.get("code_prefix", "").strip()

    # Get current academic year from global setting
    current_academic_year = get_academic_year()

    # Create an instance of the upload form
    upload_form = UploadForm()

    # Construct API parameters
    params = {
        "search": search_query,
        "page": page,
        "per_page": per_page,
        "sort": sort_by,
        "direction": sort_direction,
        "academic_year": current_academic_year  # Always include current academic year
    }

    # Add filters to params
    if status_filter == "pending":
        params["review_status"] = "pending"
    elif status_filter == "reviewed":
        params["review_status"] = "reviewed"

    if code_prefix:
        clean_prefix = code_prefix.strip().upper()
        if clean_prefix:
            params["code_prefix"] = clean_prefix

    # Make API request to fetch modules
    response = make_request('GET', '/modules', params=params)
    
    modules = []
    total_modules = 0
    total_pages = 0
    reviewers = {}

    if response.status_code == 200:
        data = response.json().get('data', {})
        modules = data.get('items', [])
        total_modules = data.get('total', 0)
        total_pages = (total_modules + per_page - 1) // per_page

        # Fetch reviewer information for all modules
        reviewer_ids = set()
        for module in modules:
            if module.get('reviewed_by'):
                if isinstance(module['reviewed_by'], dict):
                    reviewer_id = module['reviewed_by'].get('$oid')
                else:
                    reviewer_id = str(module['reviewed_by'])
                if reviewer_id:
                    reviewer_ids.add(reviewer_id)

        # Get reviewer names in bulk if there are any reviewers
        if reviewer_ids:
            try:
                users_response = make_request('GET', '/users', params={
                    'ids': list(reviewer_ids)
                })
                if users_response.status_code == 200:
                    users_data = users_response.json().get('data', {}).get('items', [])
                    reviewers = {
                        str(user.get('_id', {}).get('$oid')): user.get('username')
                        for user in users_data
                    }
            except Exception as e:
                print(f"Error fetching reviewers: {e}")

        # Enhance module data with module lead information
        for module in modules:
            # Add module lead info
            module['module_lead'], _ = get_module_lead_info(module)
            
            # Format review information
            if module.get('reviewed_by'):
                if isinstance(module['reviewed_by'], dict):
                    reviewer_id = module['reviewed_by'].get('$oid')
                else:
                    reviewer_id = str(module['reviewed_by'])
                module['reviewer_name'] = reviewers.get(reviewer_id, 'Unknown')

    # Fetch distinct code prefixes for dropdown
    try:
        prefix_response = make_request('GET', '/modules/code_prefixes')
        if prefix_response.status_code == 200:
            code_prefixes = prefix_response.json().get('data', {}).get('code_prefixes', [])
        else:
            code_prefixes = []
    except Exception as e:
        print(f"Error fetching code prefixes: {str(e)}")
        code_prefixes = []

    return render_template(
        "admin/modules.html",
        modules=modules,
        total_modules=total_modules,
        total_pages=total_pages,
        page=page,
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_direction=sort_direction,
        upload_form=upload_form,  # Pass the form to the template
        code_prefix=code_prefix,  # Pass the selected code prefix
        code_prefixes=code_prefixes,  # Pass all available code prefixes for dropdown
        reviewers=reviewers  # Add reviewers to template context
    )


@admin_bp.route("/modules/completed")
@login_required
@admin_required
def view_completed_modules():
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort", "review_date")
    sort_direction = request.args.get("direction", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = 10
    code_prefix = request.args.get("code_prefix", "").strip()

    # Get current academic year from global setting
    current_academic_year = get_academic_year()

    try:
        params = {
            "search": search_query,
            "page": page,
            "per_page": per_page,
            "review_status": "reviewed",
            "sort": sort_by,
            "direction": sort_direction,
            "academic_year": current_academic_year  # Always use global academic year
        }

        # Add code prefix filter if provided
        if code_prefix:
            params["code_prefix"] = code_prefix.upper()
        
        response = make_request('GET', '/modules', params=params)
        print(f"API Response: {response.status_code}, {response.text}")  # Debug print
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            modules = data.get('items', [])
            total_modules = data.get('total', 0)
            total_pages = (total_modules + per_page - 1) // per_page
            
            # Get reviewer names for all modules
            reviewer_ids = [str(m.get('reviewed_by', {}).get('$oid')) for m in modules if m.get('reviewed_by')]
            reviewers = {}
            
            if reviewer_ids:
                users_response = make_request('GET', '/users')
                if users_response.status_code == 200:
                    users = users_response.json().get('data', {}).get('items', [])
                    reviewers = {str(user.get('_id', {}).get('$oid')): user.get('username') for user in users}
            
            # Add reviewer names to modules
            for module in modules:
                reviewer_id = str(module.get('reviewed_by', {}).get('$oid', ''))
                module['reviewer_name'] = reviewers.get(reviewer_id, 'Unknown')

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": True,
                    "data": {
                        "modules": modules,
                        "total": total_modules,
                        "page": page,
                        "pages": total_pages
                    }
                })
            
            # Fetch distinct code prefixes
            prefix_response = make_request('GET', '/modules/code_prefixes')
            if prefix_response.status_code == 200:
                code_prefixes = prefix_response.json().get('data', {}).get('code_prefixes', [])
            else:
                code_prefixes = []
            
            # Regular template render for initial page load
            return render_template(
                "admin/completed_modules.html",
                modules=modules,
                total_modules=total_modules,
                total_pages=total_pages,
                page=page,
                search_query=search_query,
                sort_by=sort_by,
                sort_direction=sort_direction,
                code_prefix=code_prefix,
                code_prefixes=code_prefixes
            )
            
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Failed to load modules"}), 400
            flash("Error loading completed modules", "danger")
            return render_template("admin/completed_modules.html", total_pages=1)
            
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug print
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": str(e)}), 500
        flash(f"Error: {str(e)}", "danger")
        return render_template(
            "admin/completed_modules.html",
            total_pages=1,
            code_prefixes=[]
        )


@admin_bp.route("/modules/pending")
@login_required
@admin_required
def view_pending_modules():
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort", "module_code")
    sort_direction = request.args.get("direction", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    code_prefix = request.args.get("code_prefix", "").strip()

    # Get current academic year from global setting
    current_academic_year = get_academic_year()

    params = {
        "search": search_query,
        "page": page,
        "per_page": per_page,
        "review_status": "pending",
        "sort": sort_by,
        "direction": sort_direction,
        "academic_year": current_academic_year  # Always use global academic year
    }

    # Add code prefix filter if provided
    if code_prefix:
        params["code_prefix"] = code_prefix.upper()

    # Fetch modules
    response = make_request('GET', '/modules', params=params)
    modules = []
    total_modules = 0
    total_pages = 0

    if response.status_code == 200:
        data = response.json().get('data', {})
        modules = data.get('items', [])
        total_modules = data.get('total', 0)
        total_pages = (total_modules + per_page - 1) // per_page

    # Fetch distinct code prefixes
    try:
        prefix_response = make_request('GET', '/modules/code_prefixes')
        if prefix_response.status_code == 200:
            code_prefixes = prefix_response.json().get('data', {}).get('code_prefixes', [])
        else:
            code_prefixes = []
    except Exception as e:
        print(f"Error fetching code prefixes: {str(e)}")
        code_prefixes = []

    return render_template(
        "admin/pending_modules.html",
        modules=modules,
        total_modules=total_modules,
        total_pages=total_pages,
        page=page,
        search_query=search_query,
        sort_by=sort_by,
        sort_direction=sort_direction,
        code_prefix=code_prefix,
        code_prefixes=code_prefixes
    )


@admin_bp.route("/modules/upload", methods=["POST"])
@login_required
@admin_required
def upload_modules():
    form = UploadForm()
    if not form.validate_on_submit():
        return jsonify({
            "success": False,
            "message": "Invalid form submission",
            "errors": [str(err) for err in form.file.errors]
        }), 400

    try:
        file = form.file.data
        files = {"file": (file.filename, file.read(), file.mimetype)}
        response = make_request('POST', '/modules/upload', files=files)
        result = response.json()
        
        print(f"Upload API Response: {result}")  # Debug print

        if response.status_code in [200, 206]:
            # Store only essential data in session
            warnings = result['data']['warnings']
            errors = result['data']['errors']
            stats = result['data']['stats']
            
            # Truncate long messages to reduce size
            truncated_warnings = [w[:200] for w in warnings[:50]]
            truncated_errors = [e[:200] for e in errors[:50]]
            
            session['upload_summary'] = {
                'stats': {
                    'total_processed': stats.get('total_processed', 0),
                    'users_added': stats.get('users_added', 0),
                    'modules_added': stats.get('modules_added', 0),
                    'academic_year': stats.get('academic_year', datetime.utcnow().year)  # Provide default value
                },
                'warnings': truncated_warnings,
                'errors': truncated_errors,
                'timestamp': datetime.utcnow().isoformat(),
                'has_more_warnings': len(warnings) > 50,
                'has_more_errors': len(errors) > 50
            }
            
            return jsonify({
                "success": True,
                "message": result['message'],
                "redirect": url_for('admin.upload_summary')
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get('message', 'Upload failed')
            }), response.status_code

    except Exception as e:
        print(f"Upload error: {str(e)}")  # Debug print
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500


@admin_bp.route("/modules/upload/summary")
@login_required
@admin_required
def upload_summary():
    summary = session.get('upload_summary')
    if not summary:
        flash("No upload summary available", "warning")
        return redirect(url_for('admin.view_modules'))

    # Convert timestamp back to datetime
    try:
        timestamp = datetime.fromisoformat(summary.get('timestamp', ''))
    except (ValueError, TypeError):
        timestamp = datetime.utcnow()

    summary_data = {
        'stats': summary.get('stats', {
            'total_processed': 0,
            'modules_added': 0,
            'users_added': 0
        }),
        'warnings': summary.get('warnings', []),
        'errors': summary.get('errors', []),
        'timestamp': timestamp
    }

    # Clear the summary from session
    session.pop('upload_summary', None)

    return render_template('admin/upload_summary.html', **summary_data)


# ------------------------------
# Review Management
# ------------------------------
class ReviewForm(FlaskForm):
    pass

def convert_rating_to_int(rating):
    rating_map = {
        'Strongly Agree': 4,
        'Agree': 3,
        'Disagree': 2,
        'Strongly Disagree': 1
    }
    return rating_map.get(rating, 0)

def get_module_lead_info(module):
    """Helper function to fetch module lead information"""
    if not module or 'module_lead_id' not in module:
        return 'Unknown', ''

    try:
        # Handle ObjectId in dict format
        if isinstance(module['module_lead_id'], dict):
            lead_id = module['module_lead_id'].get('$oid')
        else:
            lead_id = str(module['module_lead_id'])

        if lead_id:
            lead_response = make_request('GET', f'/users/{lead_id}')
            if lead_response.status_code == 200:
                lead_data = lead_response.json().get('data', {})
                if lead_data:
                    return lead_data.get('username', 'Unknown'), lead_data.get('email', '')
    except Exception as e:
        print(f"Error fetching module lead: {e}")
    
    return 'Unknown', ''

@admin_bp.route("/modules/<module_id>/review", methods=["GET", "POST"])
@login_required
@admin_required
def review_module(module_id):
    form = ReviewForm()
    try:
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash("Invalid module ID format", "danger")
            return redirect(url_for("admin.view_pending_modules"))

        # Get module data
        response = make_request('GET', f'/modules/{clean_id}')
        
        if response.status_code == 200:
            data = response.json()
            module = data.get('data') if data.get('success') else None
            
            if module:
                # Add module lead information
                module['module_lead'], module['module_lead_email'] = get_module_lead_info(module)

                # Get existing review if any
                review_response = make_request('GET', f'/reviews/module/{clean_id}')
                if review_response.status_code == 200:
                    review_data = review_response.json()
                    if review_data.get('success'):
                        review = review_data.get('data')
                        if review and 'edit_history' in review:
                            # Get editor names for edit history
                            editor_ids = [str(edit.get('editor_id', {}).get('$oid', '')) 
                                        for edit in review['edit_history']]
                            editor_names = {}
                            
                            # Fetch all editor names in one request
                            if editor_ids:
                                editors_response = make_request('GET', '/users', 
                                                             params={'ids': editor_ids})
                                if editors_response.status_code == 200:
                                    editors_data = editors_response.json()
                                    if editors_data.get('success'):
                                        editors = editors_data.get('data', {}).get('items', [])
                                        editor_names = {
                                            str(editor.get('_id', {}).get('$oid', '')): 
                                            editor.get('username', 'Unknown')
                                            for editor in editors
                                        }
                            
                            # Add editor names to edit history
                            for edit in review['edit_history']:
                                editor_id = str(edit.get('editor_id', {}).get('$oid', ''))
                                edit['editor_name'] = editor_names.get(editor_id, 'Unknown')

        else:
            module = None

        if not module:
            flash("Module not found", "danger")
            return redirect(url_for("admin.view_pending_modules"))

        if request.method == "POST" and form.validate_on_submit():  # Add CSRF validation
            review_data = {
                "module_id": clean_id,
                "reviewer_id": str(current_user.id),
                "review_date": str(datetime.utcnow()),
                "enhancement_plan_update": request.form.get("enhancementPlan"),
                "student_attainment": request.form.get("studentAttainment"),
                "student_feedback": request.form.get("studentFeedback"),
                "risks": request.form.get("risks"),
                "engagement_rating": convert_rating_to_int(request.form.get("engagement")),
                "learning_environment_rating": convert_rating_to_int(request.form.get("learningEnvironment")),
                "timetabling_rating": convert_rating_to_int(request.form.get("timetabling")),
                "enhancement_plans": []  # Will be populated below
            }

            # Collect enhancement plans
            enhancement_plans = []
            i = 1
            while request.form.get(f"enhancementPlan{i}"):
                plan = {
                    "plan": request.form.get(f"enhancementPlan{i}"),
                    "details": request.form.get(f"enhancementDetailsText{i}")
                }
                enhancement_plans.append(plan)
                i += 1
            review_data["enhancement_plans"] = enhancement_plans

            print("Submitting review data:", review_data)  # Debug print

            res = make_request('POST', '/reviews', json=review_data)
            if res.status_code == 201:
                flash("Module review submitted successfully", "success")
                return redirect(url_for("admin.view_completed_modules"))  # Changed redirect target
            else:
                error_data = res.json()
                flash(error_data.get('message', 'Error submitting review'), "danger")

        return render_template(
            "admin/review_module.html", 
            module=module, 
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS,
            form=form  # Pass form to template
        )
        
    except Exception as e:
        print(f"Error in review_module: {str(e)}")
        flash("Error accessing module", "danger")
        return redirect(url_for("admin.view_pending_modules"))


def format_date(date_value):
    """Helper function to format MongoDB date objects"""
    if not date_value:
        return None
        
    try:
        if isinstance(date_value, dict) and '$date' in date_value:
            # Handle MongoDB ISODate format
            date_str = date_value['$date']
            if '.' in date_str:  # Handle milliseconds
                date_str = date_str.split('.')[0]
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        elif isinstance(date_value, str):
            # Try multiple date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
    except Exception as e:
        print(f"Date parsing error: {e}")
    return None

@admin_bp.route("/modules/<module_id>/view")
@login_required
@admin_required
def view_module(module_id):
    try:
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash("Invalid module ID", "danger")
            return redirect(url_for('admin.view_modules'))

        # Get module data
        response = make_request('GET', f'/modules/{clean_id}')
        print(f"Module API Response: {response.status_code}, {response.text}")

        if response.status_code != 200:
            flash("Error loading module", "danger")
            return redirect(url_for('admin.view_modules'))

        result = response.json()
        if not result.get('success'):
            flash("Failed to load module data", "danger")
            return redirect(url_for('admin.view_modules'))

        module = result.get('data')
        if not isinstance(module, dict):
            flash("Invalid module data format", "danger")
            return redirect(url_for('admin.view_modules'))

        if module:
            # Add module lead information
            module['module_lead'], module['module_lead_email'] = get_module_lead_info(module)

        # Format dates in module
        if isinstance(module.get('review_date'), dict):
            module['review_date'] = format_date(module['review_date'])

        # Get review data
        review_data = None
        if module.get('review_submitted'):
            review_response = make_request('GET', f'/reviews/module/{clean_id}')
            if review_response.status_code == 200:
                review_result = review_response.json()
                if review_result.get('success'):
                    review_data = review_result.get('data')
                    
                    # Format dates in enhancement plans
                    if isinstance(review_data, dict):
                        review_data['review_date'] = format_date(review_data.get('review_date'))
                        for plan in review_data.get('enhancement_plans', []):
                            if isinstance(plan.get('added_date'), dict):
                                plan['added_date'] = format_date(plan['added_date'])

        # When fetching review data, add editor information
        if review_data and 'edit_history' in review_data:
            editor_names = get_editor_names(review_data['edit_history'])
            for edit in review_data['edit_history']:
                editor_id = str(edit.get('editor_id', ''))
                edit['editor_name'] = editor_names.get(editor_id, 'Unknown')

        return render_template(
            "admin/view_module.html",
            module=module,
            review=review_data,
            reviewer_name=get_reviewer_name(review_data.get('reviewer_id') if review_data else None),
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS
        )

    except Exception as e:
        print(f"Error in view_module: {str(e)}")
        flash(f"Error loading module: {str(e)}", "danger")
        return redirect(url_for('admin.view_modules'))


def get_reviewer_name(reviewer_id):
    """Helper function to get reviewer name"""
    if not reviewer_id:
        return "Unknown"
        
    try:
        if isinstance(reviewer_id, dict):
            reviewer_id = reviewer_id.get('$oid')
        
        if not reviewer_id:
            return "Unknown"
            
        response = make_request('GET', f'/users/{reviewer_id}')
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data'):
                return result['data'].get('username', 'Unknown')
    except Exception as e:
        print(f"Error getting reviewer name: {e}")
    
    return "Unknown"

@admin_bp.route("/modules/<module_id>/review/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_review(module_id):
    form = ReviewForm()
    try:
        # Validate module_id
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash("Invalid module ID format", "danger")
            return redirect(url_for("admin.view_completed_modules"))

        # Get module data
        module_response = make_request('GET', f'/modules/{clean_id}')
        print(f"Module API Response: {module_response.status_code}")  # Debug log
        
        if module_response.status_code != 200:
            flash("Error loading module data", "danger")
            return redirect(url_for("admin.view_completed_modules"))

        module_data = module_response.json()
        if not module_data.get('success'):
            flash(module_data.get('message', 'Failed to load module'), "danger")
            return redirect(url_for("admin.view_completed_modules"))

        module = module_data.get('data')
        if not module:
            flash("Module not found", "danger")
            return redirect(url_for("admin.view_completed_modules"))

        # Get review data
        review_response = make_request('GET', f'/reviews/module/{clean_id}')
        print(f"Review API Response: {review_response.status_code}")  # Debug log

        if review_response.status_code != 200:
            flash("Review data not accessible", "danger")
            return redirect(url_for("admin.view_module", module_id=clean_id))

        review_data = review_response.json()
        if not review_data.get('success'):
            flash(review_data.get('message', 'Failed to load review'), "danger")
            return redirect(url_for("admin.view_module", module_id=clean_id))

        review = review_data.get('data')
        if not review:
            flash("Review not found", "danger")
            return redirect(url_for("admin.view_module", module_id=clean_id))

        # Handle form submission
        if request.method == "POST" and form.validate_on_submit():
            try:
                # Get the review ID
                review_id = str(review.get('_id', {}).get('$oid'))
                if not review_id:
                    raise ValueError("Invalid review ID")

                # Collect enhancement plans
                enhancement_plans = []
                i = 1
                while request.form.get(f"enhancementPlan{i}"):
                    plan = {
                        "plan": request.form.get(f"enhancementPlan{i}"),
                        "details": request.form.get(f"enhancementDetailsText{i}")
                    }
                    enhancement_plans.append(plan)
                    i += 1

                # Prepare update data with correct structure
                updated_review = {
                    "editor_id": str(current_user.id),
                    "data": {
                        "reviewer_id": str(current_user.id),
                        "review_date": str(datetime.utcnow()),
                        "enhancement_plan": request.form.get("enhancementPlan"),
                        "student_attainment": request.form.get("studentAttainment"),
                        "student_feedback": request.form.get("studentFeedback"),
                        "risks": request.form.get("risks"),
                        "engagement_rating": convert_rating_to_int(request.form.get("engagement")),
                        "learning_environment_rating": convert_rating_to_int(request.form.get("learningEnvironment")),
                        "timetabling_rating": convert_rating_to_int(request.form.get("timetabling")),
                        "enhancement_plans": enhancement_plans
                    }
                }

                print(f"Sending update request for review {review_id}:")
                print(f"Data: {updated_review}")

                # Make API request
                update_response = make_request('PUT', f'/reviews/{review_id}', json=updated_review)
                print(f"Update response: {update_response.status_code}")
                print(f"Response content: {update_response.text}")

                if update_response.status_code == 200:
                    flash("Review updated successfully", "success")
                    return redirect(url_for("admin.view_module", module_id=clean_id))

                error_message = "Unknown error occurred"
                try:
                    error_data = update_response.json()
                    error_message = error_data.get('message', 'Server error occurred')
                except:
                    error_message = f"Server error: {update_response.status_code}"
                
                raise ValueError(error_message)

            except Exception as e:
                print(f"Error updating review: {str(e)}")
                flash(f"Error updating review: {str(e)}", "danger")

        # Add module lead information for display
        module['module_lead'], module['module_lead_email'] = get_module_lead_info(module)

        return render_template(
            "admin/edit_review.html",
            module=module,
            review=review,
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS,
            form=form
        )

    except Exception as e:
        print(f"Error in edit_review: {str(e)}")  # Debug log
        flash(f"Error accessing review: {str(e)}", "danger")
        return redirect(url_for("admin.view_completed_modules"))

def get_editor_names(edit_history):
    editor_names = {}
    if not edit_history:
        return editor_names
        
    try:
        editor_ids = [str(edit['editor_id']) for edit in edit_history if 'editor_id' in edit]
        if editor_ids:
            response = make_request('GET', '/users', params={'ids': editor_ids})
            if response.status_code == 200:
                users = response.json().get('data', {}).get('items', [])
                editor_names = {
                    str(user['_id']): user.get('username', 'Unknown')
                    for user in users
                }
    except Exception as e:
        print(f"Error fetching editor names: {e}")
    
    return editor_names

@admin_bp.route("/modules/<module_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_module(module_id):
    try:
        clean_id = extract_object_id(module_id)
        if not clean_id:
            logger.error(f"Invalid module ID format: {module_id}")
            flash("Invalid module ID format", "danger")
            return redirect(url_for('admin.view_modules'))

        # Get module data
        response = make_request('GET', f'/modules/{clean_id}')
        
        if not response.ok:
            logger.error(f"Error fetching module {clean_id}: {response.status_code}, {response.text}")
            flash("Error loading module", "danger")
            return redirect(url_for('admin.view_modules'))

        module_data = response.json()
        if not module_data.get('success'):
            flash(module_data.get('message', 'Failed to load module'), "danger")
            return redirect(url_for('admin.view_modules'))

        module = module_data.get('data')

        # Fetch all module leads using the API with a large per_page value
        leads_response = make_request('GET', '/users', params={
            'role': 'module_lead',
            'is_active': True,
            'sort': 'username',
            'direction': 'asc',
            'per_page': 1000 
        })

        if not leads_response.ok:
            flash("Error loading module leads", "danger")
            return redirect(url_for('admin.view_modules'))

        leads_data = leads_response.json()
        module_leads = leads_data.get('data', {}).get('items', [])

        if request.method == "POST":
            module_lead_id = request.form.get('module_lead_id')
            if not module_lead_id:
                flash("Module lead is required", "danger")
                return render_template("admin/edit_module.html", module=module, module_leads=module_leads)

            # Clean module_lead_id if in MongoDB format
            if isinstance(module_lead_id, dict) and '$oid' in module_lead_id:
                module_lead_id = str(module_lead_id['$oid'])
            elif isinstance(module_lead_id, str):
                module_lead_id = module_lead_id.replace('{"$oid": "', '').replace('"}', '')

            update_data = {
                "module_code": request.form.get('module_code'),
                "module_name": request.form.get('module_name'),
                "module_lead_id": module_lead_id,
                "level": int(request.form.get('level', 0)),
                "in_use": request.form.get('in_use') == 'true'
            }

            try:
                update_response = make_request('PUT', f'/modules/{clean_id}', json=update_data)
                response_data = update_response.json()

                if update_response.ok and response_data.get('success'):
                    flash("Module Updated Successfully", "success")
                    return redirect(url_for('admin.view_modules'))
                else:
                    flash(response_data.get('message', 'Failed to update module'), "danger")

            except Exception as e:
                logger.error(f"Exception during module update: {str(e)}")
                flash("Error occurred while updating module", "danger")

        # Get current module lead info for display
        module['module_lead'], module['module_lead_email'] = get_module_lead_info(module)
        return render_template("admin/edit_module.html", module=module, module_leads=module_leads)

    except Exception as e:
        logger.error(f"Unexpected error in edit_module: {str(e)}")
        flash(f"Error accessing module: {str(e)}", "danger")
        return redirect(url_for('admin.view_modules'))

@admin_bp.route("/modules/send-reminder", methods=["POST"])
@login_required
@admin_required
def send_reminder():
    """Handle sending reminders for single or multiple modules"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
            
        # Handle both single and batch reminders
        modules = data.get('modules', [])
        if data.get('module_id'):  # Single module case
            modules.append(data['module_id'])
            
        if not modules:
            return jsonify({
                "success": False,
                "message": "No modules selected"
            }), 400

        # Store modules in flask request context for the resource to access
        request.modules = modules
        
        reminder_resource = ModuleReminderResource()
        response = reminder_resource.post()
        
        # Handle response
        if isinstance(response, dict):
            return jsonify(response)
        elif isinstance(response, tuple):
            response_data, status_code = response
            return jsonify(response_data), status_code
            
        return jsonify({
            "success": True,
            "message": "Reminders sent successfully"
        })

    except Exception as e:
        print(f"Error sending reminder(s): {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500
