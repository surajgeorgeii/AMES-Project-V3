from flask import Blueprint, jsonify, request, current_app
from .utils import set_academic_year, get_academic_year

base_bp = Blueprint('base', __name__)

@base_bp.route('/api/get-academic-year', methods=['GET'])
def get_current_academic_year():
    year = get_academic_year()
    current_app.logger.debug(f"Current academic year: {year}")
    return jsonify({'year': year})

@base_bp.route('/api/set-academic-year', methods=['POST'])
def update_academic_year():
    try:
        data = request.get_json()
        if not data or 'year' not in data:
            return jsonify({
                'success': False,
                'message': 'Year not provided'
            }), 400

        year = int(data['year'])
        current_app.logger.info(f"Setting academic year to: {year}")
        
        if set_academic_year(year):
            return jsonify({
                'success': True,
                'year': year,
                'message': f'Academic year set to {year}/{year+1}'
            })
        
        return jsonify({
            'success': False,
            'message': 'Failed to set academic year'
        }), 500
        
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid year format'
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error in update_academic_year: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500
