from flask import request, g
from flask_restful import Resource
from werkzeug.security import generate_password_hash
from bson import ObjectId
from bson.json_util import dumps
from json import loads
from datetime import datetime
from .models import User, Module, Review  
from functools import wraps
from utils.email import send_reminder_email

def format_response(data, message=None, success=True):
    """Format response with proper JSON serialization"""
    try:
        response_data = {
            "success": success,
            "message": message,
            "data": None
        }

        if data is not None:
            if isinstance(data, dict) and "data" in data:
                response_data["data"] = data["data"]
            else:
                response_data["data"] = data

        # Convert ObjectIds to strings
        json_str = dumps(response_data)
        return loads(json_str)

    except Exception as e:
        print(f"Error formatting response: {str(e)}")  # Debug print
        return {
            "success": False,
            "message": "Error formatting response",
            "data": None
        }

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            return format_response(None, "Authentication required", False), 401
        return f(*args, **kwargs)
    return decorated_function

def clean_object_id(id_value):
    """Helper function to clean and validate ObjectId"""
    try:
        if not id_value:
            return None
            
        # If it's already an ObjectId, convert to string
        if isinstance(id_value, ObjectId):
            return str(id_value)
            
        # If it's a string representation of MongoDB format
        if isinstance(id_value, str) and '$oid' in id_value:
            import json
            try:
                data = json.loads(id_value.replace("'", '"'))
                if isinstance(data, dict) and '$oid' in data:
                    return data['$oid']
            except:
                pass
        
        # Clean any string input
        clean_id = str(id_value).strip().replace('"', '').replace("'", "")
        if ObjectId.is_valid(clean_id):
            return clean_id
            
        return None
    except:
        return None

# -------------------------
# User API Resource
# -------------------------
class UserResource(Resource):
    method_decorators = [api_login_required]  # Apply to all methods
    
    def get(self, user_id=None):
        try:
            if user_id:
                print(f"Getting user with ID: {user_id}")  # Debug print
                
                # Clean the ID first
                if isinstance(user_id, dict):
                    user_id = str(user_id.get('$oid', user_id))
                else:
                    user_id = str(user_id)
                
                print(f"Cleaned user_id: {user_id}")  # Debug print
                
                if not ObjectId.is_valid(user_id):
                    print(f"Invalid ObjectId: {user_id}")  # Debug print
                    return format_response(None, "Invalid user ID format", False), 400
                
                user = User.get_user_by_id(user_id)
                if user:
                    # Convert ObjectId to string
                    user['_id'] = str(user['_id'])
                
                print(f"Found user: {user}")  # Debug print
                
                if not user:
                    return format_response(None, "User not found", False), 404
                    
                return format_response({"data": user})
                
            # Handle count-only requests
            count_only = request.args.get("count_only", "false").lower() == "true"
            if count_only:
                counts = {
                    "total": User.collection.count_documents({}),
                    "admin": User.collection.count_documents({"role": "admin"}),
                    "module_lead": User.collection.count_documents({"role": "module_lead"})
                }
                return format_response({"counts": counts})

            # Regular paginated list request
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 10))
            search = request.args.get("search", "")
            sort_by = request.args.get("sort", "username")
            sort_direction = -1 if request.args.get("direction") == "desc" else 1

            query = {}
            if search:
                query["$or"] = [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}}
                ]
            
            # Add status filter
            is_active = request.args.get("is_active")
            if is_active is not None:
                query["is_active"] = is_active == "True"

            total = User.collection.count_documents(query)
            
            # Add sort to the query
            cursor = User.collection.find(query)
            cursor = cursor.sort(sort_by, sort_direction)
            cursor = cursor.skip((page - 1) * per_page).limit(per_page)
            
            users = list(cursor)
            
            return format_response({
                "items": users,
                "total": total,
                "page": page,
                "per_page": per_page
            })
            
        except Exception as e:
            return format_response(None, str(e), False), 500

    def post(self):
        try:
            data = request.get_json()
            print(f"Received user data: {data}")  # Debug print

            if not data:
                return format_response(None, "No data provided", False), 400

            required_fields = ["username", "email", "password", "role"]
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return format_response(None, f"Missing required fields: {', '.join(missing_fields)}", False), 400

            # Check for existing user by username or email
            existing_user = User.collection.find_one({
                "$or": [
                    {"username": data["username"]},
                    {"email": data["email"]}
                ]
            })

            if existing_user:
                if existing_user["username"] == data["username"]:
                    return format_response(None, "Username already exists", False), 400
                else:
                    return format_response(None, "Email already exists", False), 400

            # Create user document
            user_data = {
                "username": data["username"],
                "email": data["email"],
                "password": generate_password_hash(data["password"]),
                "role": data["role"],
                "is_active": True,
                "created_at": datetime.utcnow()
            }

            result = User.collection.insert_one(user_data)
            
            if result.inserted_id:
                new_user = User.get_user_by_id(result.inserted_id)
                if new_user:
                    new_user['_id'] = str(new_user['_id'])  # Convert ObjectId to string
                    return format_response({"data": new_user}, "User created successfully"), 201

            return format_response(None, "Failed to create user", False), 500

        except Exception as e:
            print(f"Error creating user: {str(e)}")  # Debug print
            return format_response(None, f"Server error: {str(e)}", False), 500

    def put(self, user_id):
        try:
            print(f"Update request for user_id: {user_id}")  # Debug print
            
            # Clean and validate user_id
            clean_id = None
            if isinstance(user_id, dict):
                clean_id = str(user_id.get('$oid', ''))
            elif isinstance(user_id, str):
                clean_id = user_id
                
            if not clean_id or not ObjectId.is_valid(clean_id):
                return format_response(None, "Invalid user ID format", False), 400
            
            # Parse request data
            try:
                data = request.get_json(force=True)
                print(f"Update data received: {data}")  # Debug print
            except Exception as e:
                print(f"JSON parse error: {str(e)}")  # Debug print
                return format_response(None, "Invalid JSON data", False), 400
            
            # Update user
            result = User.update_user(clean_id, data)
            print(f"Update result: {result}")  # Debug print
            
            if result and result.modified_count > 0:
                updated_user = User.get_user_by_id(clean_id)
                if updated_user:
                    updated_user['_id'] = str(updated_user['_id'])
                return format_response({"data": updated_user}, "User updated successfully"), 200
            
            return format_response(None, "No changes made", False), 400
            
        except Exception as e:
            print(f"Update error: {str(e)}")  # Debug print
            return format_response(None, str(e), False), 500

    def delete(self, user_id):
        if not User.get_user_by_id(user_id):
            return {"message": "User not found"}, 404

        User.delete_user(user_id)
        return {"message": "User deleted successfully"}, 200

class UserEmailResource(Resource):
    method_decorators = [api_login_required]

    def post(self, user_id):
        """Send email to a specific user"""
        try:
            data = request.get_json()
            if not data:
                return format_response(None, "No data provided", False), 400

            # Validate required fields
            required_fields = ["subject", "message"]
            missing_fields = {field: ["This field is required"] 
                            for field in required_fields 
                            if not data.get(field)}
            
            if missing_fields:
                return format_response(None, "Missing required fields", False), 400

            # Clean user ID and get user
            clean_id = clean_object_id(user_id)
            if not clean_id:
                return format_response(None, "Invalid user ID", False), 400

            user = User.get_user_by_id(clean_id)
            if not user:
                return format_response(None, "User not found", False), 404

            # Get sender info from flask_login current_user
            from flask_login import current_user
            if not current_user or not current_user.email:
                return format_response(None, "Sender email not available", False), 400

            # Send email
            try:
                from utils.email import send_custom_email
                send_custom_email(
                    recipient_email=user['email'],
                    subject=data['subject'],
                    message=data['message'],
                    sender_email=current_user.email
                )
                return format_response(None, "Email sent successfully", True)
            except Exception as e:
                return format_response(None, f"Failed to send email: {str(e)}", False), 500

        except Exception as e:
            return format_response(None, f"Server error: {str(e)}", False), 500

# -------------------------
# Module API Resource
# -------------------------
class ModuleResource(Resource):
    method_decorators = [api_login_required]
    
    def get(self, module_id=None):
        try:
            if module_id:
                clean_id = clean_object_id(module_id)
                print(f"API - Fetching module {clean_id}")  # Debug print
                
                if not clean_id or not ObjectId.is_valid(clean_id):
                    return format_response(None, "Invalid module ID", False), 404

                module = Module.collection.find_one({"_id": ObjectId(clean_id)})
                if not module:
                    return format_response(None, "Module not found", False), 404

                # Convert module to dict if it's a list
                if isinstance(module, list):
                    module = module[0] if module else {}
                
                # Ensure it's a dictionary
                if not isinstance(module, dict):
                    module = dict(module)
                
                print(f"API - Found module: {module}")  # Debug print
                return format_response({"data": module})

            # Handle count-only requests
            count_only = request.args.get("count_only", "false").lower() == "true"
            if count_only:
                # Get academic year from request params
                academic_year = request.args.get("academic_year")
                query = {}
                
                if academic_year:
                    query["academic_year"] = int(academic_year)

                counts = {
                    "total": Module.collection.count_documents(query),
                    "pending": Module.collection.count_documents({
                        **query,
                        "review_submitted": False
                    }),
                    "completed": Module.collection.count_documents({
                        **query,
                        "review_submitted": True
                    })
                }
                return format_response({"counts": counts})

            # Regular paginated list request
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 10))
            
            search = request.args.get("search", "")
            sort_field = request.args.get("sort", "module_code")
            sort_direction = -1 if request.args.get("direction") == "desc" else 1
            review_status = request.args.get("review_status")
            academic_year = request.args.get("academic_year")
            code_prefix = request.args.get("code_prefix")

            # Use aggregation pipeline to join with users collection
            pipeline = []

            # Lookup stage to join with users collection
            pipeline.append({
                "$lookup": {
                    "from": "users",
                    "let": { "lead_id": "$module_lead_id" },
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": ["$_id", {"$toObjectId": "$$lead_id"}]
                                }
                            }
                        },
                        {
                            "$project": {
                                "username": 1,
                                "email": 1
                            }
                        }
                    ],
                    "as": "module_lead_info"
                }
            })

            # Unwind the module_lead_info array
            pipeline.append({"$unwind": {"path": "$module_lead_info", "preserveNullAndEmptyArrays": True}})

            # Match stage for filters
            match_conditions = {}
            
            if search:
                match_conditions["$or"] = [
                    {"module_code": {"$regex": f".*{search}.*", "$options": "i"}},
                    {"module_name": {"$regex": f".*{search}.*", "$options": "i"}},
                    {"module_lead_info.username": {"$regex": f".*{search}.*", "$options": "i"}}
                ]

            if review_status == "pending":
                match_conditions["review_submitted"] = False
            elif review_status == "reviewed":
                match_conditions["review_submitted"] = True

            if academic_year:
                try:
                    match_conditions["academic_year"] = int(academic_year)
                except ValueError:
                    return format_response(None, "Invalid academic year", False), 400

            if code_prefix:
                match_conditions["code_prefix"] = code_prefix.upper()

            if match_conditions:
                pipeline.append({"$match": match_conditions})

            # Count total documents before pagination
            count_pipeline = pipeline.copy()
            count_pipeline.append({"$count": "total"})
            total_result = list(Module.collection.aggregate(count_pipeline))
            total = total_result[0]["total"] if total_result else 0

            # Add sort stage
            pipeline.append({"$sort": {sort_field: sort_direction}})

            # Add pagination
            pipeline.append({"$skip": (page - 1) * per_page})
            pipeline.append({"$limit": per_page})

            # Execute pipeline
            modules = list(Module.collection.aggregate(pipeline))

            # Format module lead info
            for module in modules:
                if "module_lead_info" in module:
                    module["module_lead"] = module["module_lead_info"].get("username", "Unknown")
                    module["module_lead_email"] = module["module_lead_info"].get("email", "")
                    del module["module_lead_info"]
                else:
                    module["module_lead"] = "Not Assigned"
                    module["module_lead_email"] = ""

            return format_response({
                "items": modules,
                "total": total,
                "page": page,
                "per_page": per_page
            })

        except Exception as e:
            print(f"Debug - Error in ModuleResource: {str(e)}")
            return format_response(None, str(e), False), 500

    def post(self):
        data = request.json
        if not data.get("module_code") or not data.get("module_name") or not data.get("module_lead"):
            return {"message": "Missing required fields"}, 400

        Module.create_module(data["module_code"], data["module_name"], data["module_lead"])
        return {"message": "Module created successfully"}, 201

    def put(self, module_id):
        """Update a module"""
        try:
            # Validate data
            data = request.get_json()
            if not data:
                return format_response(None, "No update data provided", False), 400

            # Clean the module_id
            clean_id = clean_object_id(module_id)
            if not clean_id:
                return format_response(None, "Invalid module ID format", False), 400

            # Get current module to check existence
            module = Module.get_module_by_id(clean_id)
            if not module:
                return format_response(None, "Module not found", False), 404

            # Update module
            result = Module.update_module(clean_id, data)
            
            if result and result.modified_count > 0:
                # Fetch updated module
                updated_module = Module.get_module_by_id(clean_id)
                return format_response({
                    "data": updated_module
                }, "Module updated successfully", True), 200
            else:
                return format_response(None, "No changes were made", True), 200

        except ValueError as ve:
            print(f"Validation error: {str(ve)}")
            return format_response(None, str(ve), False), 400
        except Exception as e:
            print(f"Error updating module: {str(e)}")
            return format_response(None, "Server error occurred", False), 500

    def delete(self, module_id):
        if not Module.get_module_by_id(module_id):
            return {"message": "Module not found"}, 404

        Module.delete_module(module_id)
        return {"message": "Module deleted successfully"}, 200

# -------------------------
# Module Code Prefix API Resource
# -------------------------
class ModuleCodePrefixResource(Resource):
    method_decorators = [api_login_required]

    def get(self):
        try:
            # Get distinct code prefixes
            prefixes = Module.collection.distinct("code_prefix")
            return format_response({"code_prefixes": sorted(prefixes)})  # Sorted for UI convenience
        except Exception as e:
            return format_response(None, str(e), False), 500


# -------------------------
# Review API Resource
# -------------------------
class ReviewResource(Resource):
    method_decorators = [api_login_required]
    
    def get(self, review_id=None, module_id=None):
        try:
            if review_id:
                review = Review.get_review_by_id(review_id)
                if not review:
                    return {"success": False, "message": "Review not found"}, 404
                return format_response(review)

            if module_id:
                review = Review.get_review_by_module_id(module_id)
                if not review:
                    return {"success": False, "message": "No review found for this module"}, 404
                return format_response(review)

            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 10))

            reviews = Review.get_all_reviews(skip=(page - 1) * per_page, limit=per_page)
            return format_response(reviews)
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 500

    def post(self):
        try:
            data = request.get_json()
            if not data or not data.get("module_id") or not data.get("reviewer_id"):
                return {"success": False, "message": "Missing required fields"}, 400

            result = Review.create_review(
                module_id=data["module_id"],
                reviewer_id=data["reviewer_id"],
                enhancement_plan=data.get("enhancement_plan_update"),
                student_attainment=data.get("student_attainment"),
                student_feedback=data.get("student_feedback"),
                risks=data.get("risks"),
                engagement_rating=int(data.get("engagement_rating", 0)),
                learning_environment_rating=int(data.get("learning_environment_rating", 0)),
                timetabling_rating=int(data.get("timetabling_rating", 0)),
                enhancement_plans=data.get("enhancement_plans", [])
            )

            if result:
                # Update module review status
                Module.update_review_status(data["module_id"], data["reviewer_id"])
                return {"success": True, "message": "Review created successfully"}, 201
            
            return {"success": False, "message": "Failed to create review"}, 500
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 500

    
    def put(self, review_id):
        try:
            data = request.get_json()
            if not data:
                return format_response(None, "No data provided", False), 400

            editor_id = data.get('editor_id')
            if not editor_id:
                return format_response(None, "Editor ID is required", False), 400

            update_data = data.get('data')
            if not update_data:
                return format_response(None, "Review update data is required", False), 400

            result = Review.update_review(review_id, editor_id, data=update_data)
            return format_response(result, "Review updated successfully")

        except ValueError as e:
            return format_response(None, str(e), False), 400
        except Exception as e:
            print(f"Error updating review: {str(e)}")
            return format_response(None, "Server error occurred", False), 500

    def delete(self, review_id):
        if not Review.get_review_by_id(review_id):
            return {"message": "Review not found"}, 404

        Review.delete_review(review_id)
        return {"message": "Review deleted successfully"}, 200

# -------------------------
# Module Reminder API Resource
# -------------------------
class ModuleReminderResource(Resource):
    method_decorators = [api_login_required]

    def post(self):
        try:
            # Get modules from request context
            modules = getattr(request, 'modules', [])
            if not modules:
                data = request.get_json()
                if data and 'modules' in data:
                    modules = data['modules']
                    
            if not modules:
                return format_response(None, "No modules selected", False), 400

            module_ids = []
            for module_id in modules:
                clean_id = clean_object_id(module_id)
                if clean_id:
                    module_ids.append(clean_id)
                else:
                    print(f"Invalid module ID format: {module_id}")

            if not module_ids:
                return format_response(None, "No valid module IDs provided", False), 400

            success_count = 0
            error_messages = []

            # Group modules by module lead email
            email_groups = {}
            for module_id in module_ids:
                module = Module.get_module_by_id(module_id)
                if not module:
                    error_messages.append(f"Module {module_id} not found")
                    continue

                email = module.get('module_lead_email')
                if not email:
                    error_messages.append(f"No email found for module {module['module_code']}")
                    continue

                if email not in email_groups:
                    email_groups[email] = []
                email_groups[email].append(module)

            # Send reminders
            for email, modules in email_groups.items():
                try:
                    modules_info = [{
                        'code': m['module_code'],
                        'name': m['module_name']
                    } for m in modules]
                    
                    send_reminder_email(email, modules_info)
                    success_count += len(modules)
                except Exception as e:
                    error_messages.append(f"Failed to send email to {email}: {str(e)}")

            # Prepare response
            if success_count > 0:
                message = f"Successfully sent {success_count} reminder(s)"
                if error_messages:
                    message += f" with {len(error_messages)} error(s)"
                return format_response({
                    "success_count": success_count,
                    "errors": error_messages
                }, message, True)
            else:
                return format_response(None, 
                    f"Failed to send reminders: {'; '.join(error_messages)}", 
                    False), 500

        except Exception as e:
            return format_response(None, str(e), False), 500

