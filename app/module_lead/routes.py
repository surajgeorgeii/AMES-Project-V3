import requests
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from . import module_lead_bp
from auth.utils import module_lead_required
from bson import ObjectId
from datetime import datetime
from flask_wtf import FlaskForm
from .constants import ENHANCEMENT_PLAN_OPTIONS
from base.utils import get_academic_year

# API configuration
API_BASE_URL = "http://localhost:5000/module-lead/api"  

def make_request(method, endpoint, **kwargs):
    """Helper function to make API requests with session cookies"""
    url = f"{API_BASE_URL}{endpoint}"
    cookies = {'session': session.get('_id')}
    headers = {'X-CSRF-Token': session.get('csrf_token')}
    kwargs.update({'cookies': cookies, 'headers': headers})
    
    try:
        response = requests.request(method, url, **kwargs)
        return response
    except Exception as e:
        print(f"API Request Error: {str(e)}")
        raise

def extract_object_id(id_str):
    """Enhanced helper function to extract ObjectId from various formats"""
    try:
        if not id_str:
            return None
            
        # Handle dict format
        if isinstance(id_str, dict):
            oid = id_str.get('$oid')
            if oid and ObjectId.is_valid(str(oid)):
                return str(oid)
                
        # Handle string format
        clean_id = str(id_str).strip().replace('"', '').replace("'", "")
        if ObjectId.is_valid(clean_id):
            return clean_id
            
        # Try parsing as JSON if it contains curly braces
        if '{' in str(id_str):
            try:
                import json
                data = json.loads(str(id_str).replace("'", '"'))
                if isinstance(data, dict) and '$oid' in data:
                    oid = str(data['$oid'])
                    if ObjectId.is_valid(oid):
                        return oid
            except:
                pass
                
        return None
    except Exception as e:
        print(f"Error extracting ObjectId: {str(e)}")
        return None
    
# ------------------------------
# Module Lead Dashboard
# ------------------------------
@module_lead_bp.route("/dashboard")
@login_required
@module_lead_required
def dashboard():

    current_academic_year = get_academic_year()

    stats = {
        "total": 0,
        "pending": 0,
        "completed": 0,
        "user_total": 0,
        "user_pending": 0,
        "user_completed": 0,
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
                # Get all module counts
                counts = module_data.get("data", {}).get("counts", {})
                user_counts = module_data.get("data", {}).get("user_counts", {})
                
                # Update both total and user-specific stats
                stats.update({
                    "total": counts.get("total", 0),
                    "pending": counts.get("pending", 0),
                    "completed": counts.get("completed", 0),
                    "user_total": user_counts.get("total", 0),
                    "user_pending": user_counts.get("pending", 0),
                    "user_completed": user_counts.get("completed", 0)
                })
                
                print(f"Debug - Dashboard stats: {stats}")  # Debug print
                
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        flash(f"Error fetching dashboard data: {str(e)}", "danger")

    return render_template("module_lead/dashboard.html", stats=stats)

@module_lead_bp.route("/modules")
@login_required
@module_lead_required
def view_all_modules():
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    sort_by = request.args.get("sort", "module_code")
    sort_direction = request.args.get("direction", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    code_prefix = request.args.get("code_prefix", "").strip()

    # Get current academic year from global setting
    current_academic_year = get_academic_year()

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
                    'ids': list(reviewer_ids),
                    'per_page': 0  
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
        "module_lead/all_modules.html",
        modules=modules,
        total_modules=total_modules,
        total_pages=total_pages,
        page=page,
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_direction=sort_direction,       
        code_prefix=code_prefix,  # Pass the selected code prefix
        code_prefixes=code_prefixes,  # Pass all available code prefixes for dropdown
        reviewers=reviewers  # Add reviewers to template context
    )

@module_lead_bp.route("/modules/pending")
@login_required
@module_lead_required
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
        "module_lead/pending_modules.html",
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


@module_lead_bp.route("/modules/completed")
@login_required
@module_lead_required
def view_completed_modules():
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort", "review_date")
    sort_direction = request.args.get("direction", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = 20
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
                users_response = make_request('GET', '/users', params={
                    'ids': list(reviewer_ids),
                    'per_page': 0  
                })
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
                "module_lead/completed_modules.html",
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
            return render_template("module_lead/completed_modules.html", total_pages=1)
            
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug print
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": str(e)}), 500
        flash(f"Error: {str(e)}", "danger")
        return render_template(
            "module_lead/completed_modules.html",
            total_pages=1,
            code_prefixes=[]
        )

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

@module_lead_bp.route("/modules/<module_id>/review", methods=["GET", "POST"])
@login_required
@module_lead_required
def review_module(module_id):
    form = ReviewForm()
    try:
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash(f"Invalid module ID format: {module_id}", "danger")
            return redirect(url_for("module_lead.view_pending_modules"))

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
            return redirect(url_for("module_lead.view_pending_modules"))

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
                return redirect(url_for("module_lead.view_module", module_id=clean_id))  # Redirect to view_module
            else:
                error_data = res.json()
                flash(error_data.get('message', 'Error submitting review'), "danger")

        return render_template(
            "module_lead/review_module.html", 
            module=module, 
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS,
            form=form  # Pass form to template
        )
        
    except Exception as e:
        print(f"Error in review_module: {str(e)}")
        flash("Error accessing module", "danger")
        return redirect(url_for("module_lead.view_pending_modules"))



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

@module_lead_bp.route("/modules/<module_id>/view")
@login_required
@module_lead_required
def view_module(module_id):
    try:
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash(f"Invalid module ID format: {module_id}", "danger")
            return redirect(url_for('module_lead.view_completed_modules'))

        # Get module data
        response = make_request('GET', f'/modules/{clean_id}')
        print(f"Module API Response: {response.status_code}, {response.text}")

        if response.status_code != 200:
            flash(f"Error loading module: {response.text}", "danger")
            return redirect(url_for('module_lead.view_completed_modules'))

        result = response.json()
        if not result.get('success'):
            flash(f"Failed to load module data: {result.get('message', 'Unknown error')}", "danger")
            return redirect(url_for('module_lead.view_completed_modules'))

        module = result.get('data')
        if not isinstance(module, dict):
            flash("Invalid module data format", "danger")
            return redirect(url_for('module_lead.view_completed_modules'))

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
            "module_lead/view_module.html",
            module=module,
            review=review_data,
            reviewer_name=get_reviewer_name(review_data.get('reviewer_id') if review_data else None),
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS
        )

    except Exception as e:
        print(f"Error in view_module: {str(e)}")
        flash(f"Error loading module: {str(e)}", "danger")
        return redirect(url_for('module_lead.view_module'))


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

@module_lead_bp.route("/modules/<module_id>/review/edit", methods=["GET", "POST"])
@login_required
@module_lead_required
def edit_review(module_id):
    form = ReviewForm()
    try:
        # Validate module_id
        clean_id = extract_object_id(module_id)
        if not clean_id:
            flash("Invalid module ID format", "danger")
            return redirect(url_for("module_lead.view_completed_modules"))

        # Get module data
        module_response = make_request('GET', f'/modules/{clean_id}')
        print(f"Module API Response: {module_response.status_code}")  # Debug log
        
        if module_response.status_code != 200:
            flash("Error loading module data", "danger")
            return redirect(url_for("module_lead.view_completed_modules"))

        module_data = module_response.json()
        if not module_data.get('success'):
            flash(module_data.get('message', 'Failed to load module'), "danger")
            return redirect(url_for("module_lead.view_completed_modules"))

        module = module_data.get('data')
        if not module:
            flash("Module not found", "danger")
            return redirect(url_for("module_lead.view_completed_modules"))

        # Get review data
        review_response = make_request('GET', f'/reviews/module/{clean_id}')
        print(f"Review API Response: {review_response.status_code}")  # Debug log

        if review_response.status_code != 200:
            flash("Review data not accessible", "danger")
            return redirect(url_for("module_lead.view_module", module_id=clean_id))

        review_data = review_response.json()
        if not review_data.get('success'):
            flash(review_data.get('message', 'Failed to load review'), "danger")
            return redirect(url_for("module_lead.view_module", module_id=clean_id))

        review = review_data.get('data')
        if not review:
            flash("Review not found", "danger")
            return redirect(url_for("module_lead.view_module", module_id=clean_id))

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
                    return redirect(url_for("module_lead.view_module", module_id=clean_id))

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
            "module_lead/edit_review.html",
            module=module,
            review=review,
            enhancement_options=ENHANCEMENT_PLAN_OPTIONS,
            form=form
        )

    except Exception as e:
        print(f"Error in edit_review: {str(e)}")  # Debug log
        flash(f"Error accessing review: {str(e)}", "danger")
        return redirect(url_for("module_lead.view_completed_modules"))

def get_editor_names(edit_history):
    editor_names = {}
    if not edit_history:
        return editor_names
        
    try:
        editor_ids = [str(edit['editor_id']) for edit in edit_history if 'editor_id' in edit]
        if editor_ids:
            response = make_request('GET', '/users', params={'ids': editor_ids,'per_page': 0} )
            if response.status_code == 200:
                users = response.json().get('data', {}).get('items', [])
                editor_names = {
                    str(user['_id']): user.get('username', 'Unknown')
                    for user in users
                }
    except Exception as e:
        print(f"Error fetching editor names: {e}")
    
    return editor_names

@module_lead_bp.route("/my-modules")
@login_required
@module_lead_required
def view_your_modules():
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort", "module_code")
    sort_direction = request.args.get("direction", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    code_prefix = request.args.get("code_prefix", "").strip()

    # Get current academic year
    current_academic_year = get_academic_year()

    params = {
        "search": search_query,
        "page": page,
        "per_page": per_page,
        "sort": sort_by,
        "direction": sort_direction,
        "academic_year": current_academic_year,
        "module_lead_id": str(current_user.id)  # Filter by current user
    }

    if code_prefix:
        params["code_prefix"] = code_prefix.upper()

    try:
        response = make_request('GET', '/modules', params=params)
        
        modules = []
        total_modules = 0
        total_pages = 0
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            modules = data.get('items', [])
            
            # Format dates for each module
            for module in modules:
                if 'review_date' in module:
                    module['review_date'] = format_date(module['review_date'])
                    
            total_modules = data.get('total', 0)
            total_pages = (total_modules + per_page - 1) // per_page

        # Fetch distinct code prefixes
        prefix_response = make_request('GET', '/modules/code_prefixes')
        if prefix_response.status_code == 200:
            code_prefixes = prefix_response.json().get('data', {}).get('code_prefixes', [])
        else:
            code_prefixes = []

        return render_template(
            "module_lead/your_modules.html",
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
        
    except Exception as e:
        print(f"Error in view_my_modules: {str(e)}")
        flash("Error loading modules", "danger")
        return render_template(
            "module_lead/your_modules.html",
            modules=[],
            total_pages=1,
            code_prefixes=[]
        )
