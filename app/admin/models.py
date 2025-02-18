from bson import ObjectId
from datetime import datetime
from extensions import mongo

class User:
    collection = mongo.db.users

    @staticmethod
    def create_user(username, email, password, role):
        if not all([username, email, password, role]):
            raise ValueError("Missing required fields")
        
        user = {
            "username": username,
            "email": email,
            "password": password,  # Store hashed password
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        return User.collection.insert_one(user)

    @staticmethod
    def get_user_by_id(user_id):
        return User.collection.find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def get_all_users(query={}, sort_field="username", sort_direction=1, skip=0, limit=10):
        return list(User.collection.find(query).sort([(sort_field, sort_direction)]).skip(skip).limit(limit))

    @staticmethod
    def update_user(user_id, update_data):
        allowed_fields = {"username", "email", "role", "is_active"}
        update_dict = {k: v for k, v in update_data.items() if k in allowed_fields}
        return User.collection.update_one(
            {"_id": ObjectId(user_id)}, 
            {"$set": update_dict}
        )

class Module:
    collection = mongo.db.modules

    @staticmethod
    def create_module(module_code, code_prefix, module_name, module_lead_id, academic_year=None, in_use=True):
        if not all([module_code, module_name]):
            raise ValueError("Module code and name are required")

        if academic_year is None:
            academic_year = datetime.utcnow().year

        # Fetch module lead details
        module_lead = User.get_user_by_id(module_lead_id)
        module_lead_name = module_lead["username"] if module_lead else "Unknown"

        module = {
            "module_code": module_code,
            "module_name": module_name,
            "code_prefix": code_prefix,
            "module_lead_id": ObjectId(module_lead_id),
            "module_lead_name": module_lead_name,  # Storing module lead's name directly
            "academic_year": academic_year,
            "review_submitted": False,
            "created_at": datetime.utcnow(),
            "in_use": in_use
        }
        return Module.collection.insert_one(module)


    @staticmethod
    def get_all_modules(query={}, sort_field="module_code", sort_direction=1, skip=0, limit=10):
        pipeline = []
        
        # Match stage for filtering
        match_stage = {}
        for key, value in query.items():
            if key == 'code_prefix' and value:
                # Use substring match at the start of module_code
                match_stage['module_code'] = {'$regex': f'^{value}', '$options': 'i'}
            else:
                match_stage[key] = value
        
        if match_stage:
            pipeline.append({'$match': match_stage})

        # Add project stage to extract code prefix
        pipeline.append({
            '$addFields': {
                'code_prefix': {
                    '$substr': ['$module_code', 0, {'$indexOfBytes': ['$module_code', ' ']}]
                }
            }
        })

        # Sort stage
        pipeline.append({'$sort': {sort_field: sort_direction}})
        
        # Pagination
        pipeline.append({'$skip': skip})
        pipeline.append({'$limit': limit})

        # Execute pipeline
        try:
            modules = list(Module.collection.aggregate(pipeline))
            print(f"Pipeline result: {modules}")  # Debug log
            
            # Enhance modules with lead information
            for module in modules:
                if "module_lead_id" in module and isinstance(module["module_lead_id"], ObjectId):
                    user = User.get_user_by_id(module["module_lead_id"])
                    if user:
                        module["module_lead"] = user["username"]
                        module["module_lead_email"] = user["email"]
                    else:
                        module["module_lead"] = "Unknown"
                        module["module_lead_email"] = ""
            
            return modules
        except Exception as e:
            print(f"Error in get_all_modules: {str(e)}")
            return []

    @staticmethod
    def get_distinct_code_prefixes():
        """Get list of unique discipline codes"""
        try:
            # Extract code prefixes using regex
            pipeline = [
                {
                    '$project': {
                        'prefix': {
                            '$regexFind': {
                                'input': '$module_code',
                                'regex': '^[A-Z]+'
                            }
                        }
                    }
                },
                {
                    '$match': {
                        'prefix': {'$ne': None}
                    }
                },
                {
                    '$group': {
                        '_id': '$prefix.match'
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]
            
            result = Module.collection.aggregate(pipeline)
            prefixes = [doc['_id'] for doc in result if doc['_id']]
            print(f"Found code prefixes: {prefixes}")  # Debug log
            return sorted(prefixes)
        except Exception as e:
            print(f"Error getting code prefixes: {str(e)}")
            return []

    @staticmethod
    def get_module_by_id(module_id):
        module = Module.collection.find_one({"_id": ObjectId(module_id)})
        
        if module and "module_lead_id" in module and isinstance(module["module_lead_id"], ObjectId):
            module_lead = User.get_user_by_id(module["module_lead_id"])
            if module_lead:
                module["module_lead"] = module_lead["username"]
                module["module_lead_email"] = module_lead["email"]
            else:
                module["module_lead"] = "Unknown"
                module["module_lead_email"] = ""
        
        return module

    @staticmethod
    def update_review_status(module_id, reviewer_id):
        return Module.collection.update_one(
            {"_id": ObjectId(module_id)},
            {
                "$set": {
                    "review_submitted": True,
                    "reviewed_by": ObjectId(reviewer_id),
                    "review_date": datetime.utcnow()
                }
            }
        )

    @staticmethod
    def update_module(module_id, update_data):
        """Update module details"""
        try:
            allowed_fields = {
                "module_code", 
                "module_name", 
                "module_lead_id", 
                "level",
                "in_use"
            }
            
            update_dict = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            # Handle module_lead_id conversion
            if "module_lead_id" in update_dict:
                lead_id = update_dict["module_lead_id"]
                if isinstance(lead_id, dict) and '$oid' in lead_id:
                    lead_id = str(lead_id['$oid'])
                elif isinstance(lead_id, str):
                    try:
                        # Try parsing as dictionary string
                        import json
                        lead_dict = json.loads(lead_id.replace("'", '"'))
                        if isinstance(lead_dict, dict) and '$oid' in lead_dict:
                            lead_id = lead_dict['$oid']
                    except:
                        # If not a JSON string, use as is
                        pass
                        
                update_dict["module_lead_id"] = ObjectId(lead_id)

            return Module.collection.update_one(
                {"_id": ObjectId(module_id)},
                {"$set": update_dict}
            )
        except Exception as e:
            print(f"Error updating module: {str(e)}")
            raise

class Review:
    collection = mongo.db.module_reviews

    @staticmethod
    def create_review(**kwargs):
        review = {
            "module_id": ObjectId(kwargs['module_id']),
            "reviewer_id": ObjectId(kwargs['reviewer_id']),
            "review_date": datetime.utcnow(),
            "enhancement_plan_update": kwargs.get('enhancement_plan'),
            "student_attainment": kwargs.get('student_attainment'),
            "student_feedback": kwargs.get('student_feedback'),
            "risks": kwargs.get('risks'),
            "engagement_rating": kwargs.get('engagement_rating'),
            "learning_environment_rating": kwargs.get('learning_environment_rating'),
            "timetabling_rating": kwargs.get('timetabling_rating'),
            "enhancement_plans": kwargs.get('enhancement_plans', []),
            "edit_history": [{
                "editor_id": ObjectId(kwargs['reviewer_id']),
                "edit_date": datetime.utcnow(),
                "action": "Created"
            }]
        }
        return Review.collection.insert_one(review)

    @staticmethod
    def get_review_by_id(review_id):
        """Get a review by its ID"""
        try:
            if not isinstance(review_id, (str, ObjectId)):
                raise ValueError("Invalid review ID format")
                
            review = Review.collection.find_one({"_id": ObjectId(review_id)})
            if not review:
                raise ValueError("Review not found")
                
            return review
            
        except Exception as e:
            print(f"Error getting review by ID: {str(e)}")
            raise

    @staticmethod
    def update_review(review_id, editor_id, **kwargs):
        """Update a review with edit history"""
        try:
            print(f"Updating review {review_id}")
            print(f"Editor ID: {editor_id}")
            print(f"Update data: {kwargs}")

            if not review_id or not editor_id:
                raise ValueError("Review ID and editor ID are required")

            # Get update data
            update_data = kwargs.get('data')
            if not update_data:
                raise ValueError("No update data provided")

            # Validate required fields
            required_fields = [
                'enhancement_plan',
                'student_attainment',
                'student_feedback',
                'risks',
                'engagement_rating',
                'learning_environment_rating',
                'timetabling_rating',
                'enhancement_plans'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in update_data or update_data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            try:
                # Create edit record
                edit_record = {
                    "editor_id": ObjectId(editor_id),
                    "edit_date": datetime.utcnow(),
                    "action": "Edited"
                }

                # Update document
                result = Review.collection.update_one(
                    {"_id": ObjectId(review_id)},
                    {
                        "$set": {
                            "review_date": update_data['review_date'],
                            "reviewer_id": ObjectId(update_data['reviewer_id']),
                            "enhancement_plan_update": update_data['enhancement_plan'],
                            "student_attainment": update_data['student_attainment'],
                            "student_feedback": update_data['student_feedback'],
                            "risks": update_data['risks'],
                            "engagement_rating": update_data['engagement_rating'],
                            "learning_environment_rating": update_data['learning_environment_rating'],
                            "timetabling_rating": update_data['timetabling_rating'],
                            "enhancement_plans": update_data['enhancement_plans']
                        },
                        "$push": {"edit_history": edit_record}
                    }
                )

                if not result.modified_count:
                    raise ValueError("No changes were made to the review")

                return result

            except Exception as e:
                print(f"Database error: {str(e)}")
                raise ValueError(f"Failed to update review: {str(e)}")

        except ValueError as e:
            print(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            print(f"Error updating review: {str(e)}")
            raise ValueError(f"Unexpected error: {str(e)}")

    @staticmethod
    def get_review_by_module_id(module_id):
        try:
            if not isinstance(module_id, (str, ObjectId)):
                raise ValueError("Invalid module ID format")
                
            review = Review.collection.find_one({"module_id": ObjectId(module_id)})
            if not review:
                raise ValueError("Review not found")
                
            return review
            
        except Exception as e:
            print(f"Error getting review: {str(e)}")
            raise