from django.contrib.auth.models import AnonymousUser

def apply_clinic_filter(queryset, request_or_user, clinic_field='clinic'):
    """
    Filters a queryset based on the logged-in user's role and assigned clinic.
    - Super admins / Role ADMIN: No filter applied.
    - Clinic users: Filtered by user.profile.clinic.
    
    This utility is located in analytics/utils/filters.py to prevent circular 
    imports between the services and views layers.
    """
    if hasattr(request_or_user, 'user'):
        user = request_or_user.user
    else:
        user = request_or_user

    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return queryset.none()
    
    # Try to get UserProfile
    try:
        profile = user.profile
    except Exception:
        # Fallback if profile doesn't exist (e.g. system admin)
        if user.is_superuser:
            return queryset
        return queryset.none()

    if profile.role == 'ADMIN' or user.is_superuser:
        return queryset
    
    if profile.role == 'CLINIC_USER' and profile.clinic:
        filter_kwargs = {clinic_field: profile.clinic}
        return queryset.filter(**filter_kwargs)
    
    return queryset.none()
