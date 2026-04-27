from typing import Union, Any
from django.db.models import QuerySet
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest

def apply_clinic_filter(
    queryset: QuerySet, 
    request_or_user: Union[HttpRequest, User, Any], 
    clinic_field: str = 'clinic'
) -> QuerySet:
    """
    Filters a queryset based on the logged-in user's role and assigned clinic.
    
    Logic:
    - Super admins or users with role 'ADMIN': No filter applied (access to all clinics).
    - Users with role 'CLINIC_USER': Filtered by their assigned clinic.
    - Anonymous or unauthenticated users: Returns an empty queryset for safety.
    
    Note: This utility is located in analytics/utils/filters.py to prevent 
    circular imports between the services and views layers.
    """
    # 1. Extract user object
    if request_or_user is None:
        return queryset

    if hasattr(request_or_user, 'user'):
        user = request_or_user.user
    else:
        user = request_or_user

    # 2. Authentication and basic safety checks
    if not user or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
        return queryset.none()
    
    # 3. Superuser bypass (system administrators)
    if getattr(user, 'is_superuser', False):
        return queryset

    # 4. Profile-based role filtering
    try:
        profile = getattr(user, 'profile', None)
        if not profile:
            # Authenticated users without profiles are restricted by default
            return queryset.none()

        role = getattr(profile, 'role', None)
        
        # ADMINs can see data across all clinics
        if role == 'ADMIN':
            return queryset
        
        # CLINIC_USERs are restricted to their assigned clinic
        if role == 'CLINIC_USER' and getattr(profile, 'clinic_id', None):
            filter_kwargs = {f"{clinic_field}_id": profile.clinic_id}
            return queryset.filter(**filter_kwargs)
            
    except Exception:
        # Final safety fallback to prevent accidental data leaks
        return queryset.none()
    
    # Default to no access if role is unrecognized
    return queryset.none()
