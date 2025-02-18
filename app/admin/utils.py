from flask import request, jsonify
from flask_restful import Resource
from werkzeug.utils import secure_filename
import pandas as pd
from extensions import mongo
from werkzeug.security import generate_password_hash
import io
import re
import logging
import magic  # For MIME type validation
from bson import ObjectId
from .resources import format_response
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

# Column Mapping for Excel
EXCEL_COLUMNS = {
    'module_code': ['module code', 'module', 'code'],
    'module_name': ['name', 'module name'],
    'level': ['level'],
    'tutor': ['tutor', 'module lead', 'lecturer'],
    'in_use': ['in use', 'active', 'status']
}

MODULE_CODE_PATTERN = r"^[A-Z]{2}[0-9]{5}$"  # Example: AC11001
ALTERNATE_MODULE_CODE_PATTERN = r"^[A-Z]{8}[0-9]{1}$" # Example: INDPLACE1
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def find_column_match(columns, possible_names):
    columns_lower = [col.lower().strip() for col in columns]
    for name in possible_names:
        if name in columns_lower:
            return columns[columns_lower.index(name)]
    return None


def normalize_email(username):
    return f"{username.replace(' ', '').lower()}@ames.edu.eu"


def validate_object_id(id_str):
    try:
        return bool(ObjectId(id_str))
    except:
        return False


def sanitize_query(query):
    if not isinstance(query, dict):
        return {}
    return {k: v for k, v in query.items() if v is not None}


def handle_user_creation(username, existing_users, duplicates, new_users, warnings):
    if not username:
        return False, None

    email = normalize_email(username)

    # Check if user already exists
    if username in existing_users:
        return True, ObjectId(existing_users[username]['id'])  # Return ObjectId

    if username in duplicates['users']:
        return True, ObjectId(duplicates['users'][username])  # Return already created user's ObjectId

    # Create new user
    user_data = {
        "_id": ObjectId(),  # Generate ObjectId
        "username": username,
        "email": email,
        "password": generate_password_hash(username.replace(" ", "").lower()),
        "role": "module_lead",
        "is_active": True
    }
    new_users.append(user_data)
    duplicates['users'][username] = str(user_data['_id'])
    existing_users[username] = {'id': str(user_data['_id']), 'email': email}
    return True, user_data['_id']


def get_academic_year():
    """Helper function to get current academic year based on academic calendar"""
    today = datetime.utcnow()
    # Academic year starts in September
    # If we're in January-August, we're in the previous year's academic year
    # If we're in September-December, we're in the current year's academic year
    if today.month < 9:  # If before September
        return today.year - 1
    return today.year


class ModuleUploadResource(Resource):
    def post(self):
        try:
            if 'file' not in request.files:
                return format_response(None, "No file uploaded", False), 400

            file = request.files['file']
            filename = secure_filename(file.filename)

            # Validate file size
            file.seek(0, io.SEEK_END)
            if file.tell() > MAX_FILE_SIZE:
                return format_response(None, "File size exceeds 10MB limit", False), 400
            file.seek(0)

            # Validate MIME type
            mime_type = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)  # Reset file pointer
            if mime_type not in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                return format_response(None, "Invalid file type. Please upload .xlsx or .xls", False), 400

            try:
                df = pd.read_excel(io.BytesIO(file.read()))
            except Exception:
                return format_response(None, "Error reading the Excel file", False), 400

            column_mapping = {}
            missing_columns = []
            for key, possible_names in EXCEL_COLUMNS.items():
                matched_col = find_column_match(df.columns, possible_names)
                if matched_col:
                    column_mapping[key] = matched_col
                elif key != 'in_use':
                    missing_columns.append(f"{key} ({'/'.join(possible_names)})")

            if missing_columns:
                return jsonify({"success": False, "message": "Missing required columns", "errors": missing_columns}), 400

            new_modules = []
            new_users = []
            errors = []
            warnings = []
            duplicates = {'modules': set(), 'users': {}}  # Changed to dict for users
            academic_year = get_academic_year()

            existing_modules = {
                (m["module_code"], m["academic_year"]) 
                for m in mongo.db.modules.find(
                    {"academic_year": academic_year}, 
                    {"module_code": 1, "academic_year": 1}
                )
            }

            existing_users = {
                u["username"]: {'id': str(u['_id']), 'email': u['email']} 
                for u in mongo.db.users.find({}, {"username": 1, "email": 1})
            }

            for idx, row in df.iterrows():
                try:
                    module_code = str(row[column_mapping['module_code']]).strip()
                    module_name = str(row[column_mapping['module_name']]).strip()
                    level = str(row[column_mapping['level']]).strip()
                    module_lead = str(row.get(column_mapping.get('tutor', ''), '')).strip()
                    in_use_value = str(row.get(column_mapping.get('in_use', ''), 'N')).strip().lower()
                    in_use = in_use_value in ("y", "yes", "1", "true", "active")

                    if not module_code or not module_name or not level:
                        errors.append(f"Row {idx + 2}: Missing required fields")
                        continue

                    if not (re.match(MODULE_CODE_PATTERN, module_code) or re.match(ALTERNATE_MODULE_CODE_PATTERN, module_code)):
                        errors.append(f"Row {idx + 2}: Invalid module code '{module_code}'")
                        continue

                    # Extract the first two letters (code prefix)
                    code_prefix = module_code[:2]

                    if (module_code, academic_year) in existing_modules or module_code in duplicates['modules']:
                        warnings.append(f"Module code '{module_code}' already exists for academic year {academic_year} - skipped")
                        continue

                    # Create or get user ID
                    user_created, user_id = handle_user_creation(
                        module_lead, existing_users, duplicates, new_users, warnings
                    )

                    module_data = {
                        "module_code": module_code,
                        "code_prefix": code_prefix,  # Adding extracted code prefix
                        "module_name": module_name,
                        "level": level,
                        "module_lead_id": user_id if user_id else None,  # Store user ID instead of username
                        "in_use": in_use,
                        "review_submitted": False,
                        "academic_year": academic_year,
                    }
                    new_modules.append(module_data)
                    duplicates['modules'].add(module_code)
                    existing_modules.add((module_code, academic_year))

                    if module_lead:
                        handle_user_creation(module_lead, existing_users, duplicates, new_users, warnings)

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")

            try:
                if new_modules:
                    mongo.db.modules.insert_many(new_modules, ordered=False)
                if new_users:
                    mongo.db.users.insert_many(new_users, ordered=False)
            except Exception as e:
                errors.append(f"Some records failed to insert: {str(e)}")

            response_data = {
                "stats": {
                    "total_processed": len(df),
                    "modules_added": len(new_modules),
                    "users_added": len(new_users),
                    "academic_year": academic_year  # Add academic year to stats
                },
                "warnings": warnings,
                "errors": errors
            }

            success = len(errors) == 0
            status_code = 200 if success else 206  # 206 Partial Content if there were errors
            
            return {
                "success": success,
                "message": "File processed successfully" if success else "File processed with warnings",
                "data": response_data
            }, status_code

        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "data": None
            }, 500
