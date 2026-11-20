"""Role helpers and decorators. Put this file in the same app as models.py.

Roles
- Patient: any logged-in user with no dentist profile and is_staff=False
- Doctor:  a user linked to an ACTIVE Dentist (Dentist.user). Does NOT need is_staff.
- Staff:   is_staff=True (reception/admin). Full clinic dashboard.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import Dentist


def get_dentist(user):
    """The active Dentist profile linked to this user, or None."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return None
    try:
        dentist = user.dentist_profile
    except Dentist.DoesNotExist:
        return None
    return dentist if dentist.is_active else None


def role_home(user):
    """URL name a user should land on after login."""
    if user.is_staff:
        return "admin_dashboard"
    if get_dentist(user):
        return "doctor_schedule"
    return "dashboard"


def staff_required(view):
    """Staff only. Anonymous -> login page. Logged in but not staff -> 403."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (user.is_active and user.is_staff):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def doctor_required(view):
    """Doctors only. Sets request.dentist. Anonymous -> login page, anyone else -> 403."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        dentist = get_dentist(user)
        if dentist is None:
            raise PermissionDenied
        request.dentist = dentist
        return view(request, *args, **kwargs)
    return wrapper