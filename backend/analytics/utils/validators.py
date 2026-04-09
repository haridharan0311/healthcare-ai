"""
Input validation and data sanitization utilities.

This module provides validators for API parameters and data inputs:
- Date range validation
- Numeric parameter validation
- Disease name validation
- District validation
- Query parameter extraction & parsing

Usage:
    from analytics.utils.validators import (
        validate_date_range, 
        validate_positive_int,
        parse_query_days
    )
    
    start, end = validate_date_range(
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    
    days = parse_query_days(request.query_params, default=30)
"""

from datetime import date, timedelta, datetime
from typing import Tuple, Optional, Any, Dict
from django.db.models import Max
from analytics.models import Appointment


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_date_range(
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    max_days: int = 730,
    relative_to_latest_db: bool = True
) -> Tuple[date, date]:
    """
    Validate and normalize date range for analytics queries.
    
    For new users: Ensures dates are valid, properly ordered, and within
    reasonable limits. By default uses the latest date in the database.
    
    Args:
        start_date: Start date (string "YYYY-MM-DD" or date object)
        end_date: End date (string "YYYY-MM-DD" or date object)
        max_days: Maximum allowed range in days (default: 730 = 2 years)
        relative_to_latest_db: If True, dates are relative to latest DB date
    
    Returns:
        Tuple of (start_date, end_date) as date objects
    
    Raises:
        ValidationError: If dates are invalid or range exceeds max_days
    
    Examples:
        # From string dates
        start, end = validate_date_range("2024-01-01", "2024-12-31")
        
        # Using date objects
        start, end = validate_date_range(
            datetime.now().date() - timedelta(days=30),
            datetime.now().date()
        )
        
        # With custom max range
        start, end = validate_date_range(
            "2024-01-01",
            "2024-12-31",
            max_days=365
        )
    """
    # Get reference end date
    if relative_to_latest_db:
        latest = Appointment.objects.aggregate(Max('appointment_datetime'))['latest']
        ref_end = latest.date() if latest else date.today()
    else:
        ref_end = date.today()
    
    # Parse end_date
    if end_date is None:
        end = ref_end
    elif isinstance(end_date, str):
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")
    else:
        end = end_date
    
    # Parse start_date
    if start_date is None:
        start = end - timedelta(days=30)
    elif isinstance(start_date, str):
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
    else:
        start = start_date
    
    # Validation checks
    if start > end:
        raise ValidationError(f"start_date ({start}) cannot be after end_date ({end})")
    
    date_range = (end - start).days
    if date_range > max_days:
        raise ValidationError(
            f"Date range ({date_range} days) exceeds maximum allowed ({max_days} days)"
        )
    
    return start, end


def validate_positive_int(
    value: Any,
    field_name: str = "value",
    default: Optional[int] = None,
    min_value: int = 1,
    max_value: Optional[int] = None
) -> int:
    """
    Validate and convert value to positive integer.
    
    For new users: Safely converts strings, floats, or other types to integers
    with validation boundaries.
    
    Args:
        value: Value to validate
        field_name: Name for error messages
        default: Default value if conversion fails
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (optional)
    
    Returns:
        Validated integer value
    
    Raises:
        ValidationError: If validation fails and no default provided
    
    Examples:
        days = validate_positive_int(
            request.query_params.get('days'),
            field_name='days',
            default=30,
            min_value=1,
            max_value=365
        )
    """
    try:
        result = int(value)
    except (ValueError, TypeError):
        if default is not None:
            return default
        raise ValidationError(f"{field_name} must be a number, got: {value}")
    
    if result < min_value:
        raise ValidationError(
            f"{field_name} must be >= {min_value}, got: {result}"
        )
    
    if max_value is not None and result > max_value:
        raise ValidationError(
            f"{field_name} must be <= {max_value}, got: {result}"
        )
    
    return result


def validate_disease_name(disease_name: str) -> str:
    """
    Validate and sanitize disease name.
    
    For new users: Ensures disease name is non-empty after stripping whitespace.
    
    Args:
        disease_name: Disease name to validate
    
    Returns:
        Sanitized disease name
    
    Raises:
        ValidationError: If disease name is empty
    
    Example:
        disease = validate_disease_name(request.query_params.get('disease'))
    """
    if not isinstance(disease_name, str):
        raise ValidationError(f"disease_name must be string, got: {type(disease_name)}")
    
    sanitized = disease_name.strip()
    if not sanitized:
        raise ValidationError("disease_name cannot be empty")
    
    return sanitized


def validate_district_name(district_name: str) -> str:
    """
    Validate and sanitize district name.
    
    For new users: Ensures district name is non-empty after stripping whitespace.
    
    Args:
        district_name: District name to validate
    
    Returns:
        Sanitized district name
    
    Raises:
        ValidationError: If district name is empty
    
    Example:
        district = validate_district_name(
            request.query_params.get('district')
        )
    """
    if not isinstance(district_name, str):
        raise ValidationError(f"district_name must be string, got: {type(district_name)}")
    
    sanitized = district_name.strip()
    if not sanitized:
        raise ValidationError("district_name cannot be empty")
    
    return sanitized


def parse_query_days(
    query_params: Dict[str, str],
    default: int = 30,
    min_value: int = 1,
    max_value: int = 730
) -> int:
    """
    Parse and validate 'days' query parameter.
    
    For new users: Commonly used helper for APIs that accept ?days= parameter.
    Handles conversion, defaults, and boundary checks.
    
    Args:
        query_params: Query parameters from request (e.g. request.query_params)
        default: Default if not provided
        min_value: Minimum days allowed
        max_value: Maximum days allowed
    
    Returns:
        Validated days count
    
    Example:
        def get(self, request):
            days = parse_query_days(request.query_params, default=30)
            start, end = validate_date_range(
                end_date=date.today(),
                start_date=date.today() - timedelta(days=days)
            )
    """
    try:
        days_str = query_params.get('days', str(default))
        days = int(days_str)
    except (ValueError, TypeError):
        return default
    
    # Enforce boundaries
    days = max(days, min_value)
    days = min(days, max_value)
    
    return days


def validate_query_params(
    query_params: Dict[str, str],
    required: Optional[list] = None,
    optional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate multiple query parameters at once.
    
    For new users: Useful for APIs with many query parameters. Validates
    required fields and applies defaults to optional ones.
    
    Args:
        query_params: Query parameters dictionary
        required: List of required parameter names
        optional: Dict of {param_name: default_value}
    
    Returns:
        Dictionary of validated parameters
    
    Raises:
        ValidationError: If required parameter missing
    
    Example:
        params = validate_query_params(
            request.query_params,
            required=['disease'],
            optional={'days': 30, 'district': 'Unknown'}
        )
        disease = params['disease']
        days = params['days']
    """
    result = {}
    
    if required:
        for param in required:
            if param not in query_params:
                raise ValidationError(f"Required parameter missing: {param}")
            result[param] = query_params[param]
    
    if optional:
        for param, default in optional.items():
            result[param] = query_params.get(param, default)
    
    return result


class APIParameterValidator:
    """
    Validator class for common API parameter patterns.
    
    For new users: Reusable validator for common query parameter patterns.
    Provides chainable validation methods.
    
    Example:
        validator = APIParameterValidator(request.query_params)
        params = (validator
            .add_int('days', default=30, min_value=1, max_value=365)
            .add_string('disease', optional=True)
            .validate())
    """
    
    def __init__(self, query_params: Dict[str, str]):
        """Initialize with query parameters."""
        self.query_params = query_params
        self.rules = {}
    
    def add_int(
        self,
        name: str,
        default: Optional[int] = None,
        min_value: int = 1,
        max_value: Optional[int] = None,
        required: bool = False
    ) -> 'APIParameterValidator':
        """
        Add integer parameter validation rule.
        
        Args:
            name: Parameter name
            default: Default value if not provided
            min_value: Minimum value allowed
            max_value: Maximum value allowed
            required: Whether parameter is required
        
        Returns:
            Self for chaining
        """
        self.rules[name] = {
            'type': 'int',
            'default': default,
            'min_value': min_value,
            'max_value': max_value,
            'required': required
        }
        return self
    
    def add_string(
        self,
        name: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> 'APIParameterValidator':
        """
        Add string parameter validation rule.
        
        Args:
            name: Parameter name
            default: Default value if not provided
            required: Whether parameter is required
        
        Returns:
            Self for chaining
        """
        self.rules[name] = {
            'type': 'string',
            'default': default,
            'required': required
        }
        return self
    
    def validate(self) -> Dict[str, Any]:
        """
        Perform validation and return validated parameters.
        
        Returns:
            Dictionary of validated parameters
        
        Raises:
            ValidationError: If validation fails
        """
        result = {}
        
        for name, rule in self.rules.items():
            value = self.query_params.get(name)
            
            if value is None:
                if rule['required']:
                    raise ValidationError(f"Required parameter missing: {name}")
                result[name] = rule.get('default')
            elif rule['type'] == 'int':
                result[name] = validate_positive_int(
                    value,
                    field_name=name,
                    default=rule.get('default'),
                    min_value=rule.get('min_value', 1),
                    max_value=rule.get('max_value')
                )
            elif rule['type'] == 'string':
                result[name] = validate_disease_name(value)
        
        return result
