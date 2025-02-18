from datetime import datetime
from flask import session, current_app

def get_academic_year():
    """Get academic year from session or calculate current academic year"""
    if 'academic_year' in session:
        year = int(session['academic_year'])
        current_app.logger.debug(f"Retrieved academic year from session: {year}")
        return year
    
    today = datetime.utcnow()
    current_year = today.year
    
    # If we're in January-August, we're in the previous year's academic year
    academic_year = current_year - 1 if today.month < 9 else current_year
    
    # Store in session
    session['academic_year'] = academic_year
    current_app.logger.debug(f"Calculated and stored academic year: {academic_year}")
    return academic_year

def get_academic_year_display(year=None):
    """
    Returns the academic year in display format (YYYY/YYYY)
    Example: 2023/2024
    """
    if year is None:
        year = get_academic_year()
    return f"{year}/{year + 1}"

def set_academic_year(year):
    """Set academic year in session"""
    try:
        year = int(year)
        session['academic_year'] = year
        return True
    except (ValueError, TypeError):
        return False
