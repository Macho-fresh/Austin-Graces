from django.shortcuts import render, redirect
from .models import *
from django.contrib.auth import authenticate, login as auth_login
from .forms import *
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
import datetime
from django.utils.dateparse import parse_date
from django.db import transaction

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Appointment
from .permissions import doctor_required
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Appointment, Dentist
from .permissions import staff_required

@login_required
def home(request):
    featured_services = Service.objects.filter(is_published = True)[:3]
    featured_dentists = Dentist.objects.filter(is_active = True)[:3]


    context = {
        'featured_services': featured_services,
        'featured_dentists': featured_dentists
    }
    return render(request, 'home.html', context)

def dentist_detail(request, slug):
    dentist = get_object_or_404(
        Dentist,
        slug=slug,
        is_active=True
    )

    return render(request, 'dentist_detail.html', {
        'dentist': dentist
    })

def service_detail(request, slug):
    service = get_object_or_404(
        Service,
        slug=slug,
        is_published=True
    )

    return render(request, 'service_detail.html', {
        'service': service
    })

@login_required
def appointment(request):

    return render(request, 'appointment.html')

@login_required
def appointment_slots(request):
    return render(request, 'appointment_slots.html')

@login_required
def services(request):
    return render(request, 'services.html')

@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def dentists(request):
    return render(request, 'dentists.html')

@login_required
def testimonials(request):
    return render(request, 'testimonials.html')

@login_required
def faq(request):
    return render(request, 'faq.html')

@login_required
def contact(request):
    return render(request, 'contact.html')


class EmailOrUsernameAuthForm(AuthenticationForm):
    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")
        if identifier and password:
            account = (User.objects.filter(username__iexact=identifier).first()
                       or User.objects.filter(email__iexact=identifier).first())
            username = account.get_username() if account else identifier
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


def login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = EmailOrUsernameAuthForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        next_url = request.POST.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


def register(request):
    if request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)

            messages.success(
                request,
                'Welcome, your account has been created'
            )

            return redirect('login')

    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {"form": form})

@login_required
def password_reset(request):
    return render(request, 'registration/ag_password_reset_form.html')

@login_required
def password_reset_confirm(request):
    return render(request, 'registration/ag_password_reset_confirm.html')

def logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return render(request, 'accounts/login.html')

@login_required
def blog(request):
    return render(request, 'blog.html')

@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

@login_required
def my_appointments(request):
    return render(request, 'accounts/my_appointments.html')

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

@login_required
def appointments(request):

    return render(request, 'accounts/appointments.html')

@login_required
def password_change(request):
    return render(request, 'registration/ag_password_change.html')

@login_required
def admin_dashboard(request):
    return render(request, 'clinic_admin/dashboard.html')

@login_required
def admin_appointments(request):
    if request.method == 'GET':
        q = request.GET.get('q', '').strip()
        date_from = parse_date(request.GET.get('date_from', ''))
        date_to = parse_date(request.GET.get('date_to', ''))
        service = request.GET.get('service', '').strip()
        status = request.GET.get('status', '').strip()
        
        appointment = Appointment.objects.all()
        if q:
            appointment = Appointment.objects.filter(Q(email__iexact=q) | Q(full_name__iexact=q) | Q(phone__icontains=q))

        if date_from:
            appointment = appointment.filter(date__gte=date_from)
        if date_to:
            appointment = appointment.filter(date__lte=date_to)

        if service.isdigit():
            appointment = appointment.filter(service_id=int(service))

        valid_status = []
        for i in Appointment.Status.choices:
            valid_status.append(i)

        if status and status in valid_status:
            appointment = appointment.filter(status=status)

        paginator = Paginator(appointment, 15)
        page_obj = paginator.get_page(request.GET.get('page'))

        # Preserve filters when moving between pages
        params = request.GET.copy()
        params.pop('page', None)

        query_string = '&' + params.urlencode() if params else ''
        services = Service.objects.all()

    return render(request, 'clinic_admin/appointments.html', {
        'services': services,
        'status_choices': Appointment.Status.choices,
        'query_string': query_string,
        'page_obj': appointment
    })

@login_required
def admin_patients(request):
    if request.method == 'GET':
        patients = User.objects.filter(
        dentist_profile__isnull=True,
        is_staff=False,
        is_superuser=False
        )

    context = {
        'page_obj': patients
    }
    return render(request, 'clinic_admin/patients.html', context)


@login_required
def admin_patient_edit(request, pk):
    patient = get_object_or_404(
        User,
        pk=pk,
        dentist_profile__isnull=True,
        is_staff=False,
        is_superuser=False
    )

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not first_name or not last_name or not email:
            messages.error(request, 'First name, last name and email are required.')
            return redirect('admin_patients')

        if User.objects.filter(email=email).exclude(pk=patient.pk).exists():
            messages.error(request, 'A user with this email already exists.')
            return redirect('admin_patients')

        patient.first_name = first_name
        patient.last_name = last_name
        patient.email = email
        patient.phone = phone
        patient.save()

        messages.success(request, 'Patient details updated successfully.')
        return redirect('admin_patients')

    return redirect('admin_patients')

# @login_required
# def admin_dentists_add(request):
#     if request.method == 'POST':
#         full_name = request.POST.get('full_name', '').strip()
#         title = request.POST.get('title', '').strip()
#         specialization = request.POST.get('specialization', '').strip()
#         experience_years = request.POST.get('experience_years', '').strip()
#         qualifications = request.POST.get('qualifications', '').strip()
#         bio = request.POST.get('bio', '').strip()
#         photo = request.FILES.get('photo')

#         if Dentist.objects.filter(full_name__iexact = full_name).exists():
#             messages.error(request, 'Dentist already exists')
#             return render(request, 'clinic_admin/dentists.html')

#         if experience_years:
#             try:
#                 experience_years = int(experience_years)
#             except ValueError:
#                 messages.error(request, 'Enter a valid number of years.')
#                 return render(request, 'clinic_admin/dentists.html')
#         else:
#             experience_years = None

#         Dentist.objects.create(
#             full_name = full_name,
#             title = title,
#             specialization = specialization,
#             experience_years = experience_years,
#             qualifications = qualifications,
#             bio = bio,
#             photo = photo
#         )

#         messages.success(request, 'Dentist added successfully')
#         return redirect('admin_dentists')
#     return render(request, 'clinic_admin/dentists.html')

# @login_required
# def admin_dentist_edit(request, pk):
#     dentist = get_object_or_404(Dentist, pk=pk)

#     if request.method == 'POST':
#         dentist.full_name = request.POST.get('full_name', '').strip()
#         dentist.title = request.POST.get('title', '').strip()
#         dentist.specialization = request.POST.get('specialization', '').strip()
#         dentist.qualifications = request.POST.get('qualifications', '').strip()
#         dentist.bio = request.POST.get('bio', '').strip()

#         experience_years = request.POST.get('experience_years', '').strip()
#         dentist.experience_years = int(experience_years) if experience_years else None

#         if request.FILES.get('photo'):
#             dentist.photo = request.FILES.get('photo')

#         dentist.save()

#         messages.success(request, 'Dentist updated successfully.')
#         return redirect('admin_dentists')

#     return redirect('admin_dentists')

# # @staff_member_required
# def admin_dentist_delete(request, pk):
#     dentist = get_object_or_404(Dentist, pk=pk)

#     if request.method == 'POST':
#         dentist.delete()
#         messages.success(request, 'Dentist deleted successfully.')
#         return redirect('admin_dentists')

#     return redirect('admin_dentists')

# @require_POST
# def admin_dentist_toggle(request, pk):
#     dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
#     with transaction.atomic():
#         dentist.is_active = not dentist.is_active
#         dentist.save(update_fields=["is_active"])
#         # sync_user_active(dentist)
#     if dentist.is_active:
#         messages.success(request, f"{dentist.full_name} is now active.")
#     else:
#         pending = Appointment.objects.filter(
#             dentist=dentist, status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
#             date__gte=timezone.localdate()).count()
#         messages.success(request, f"{dentist.full_name} is now inactive.")
#         if pending:
#             messages.warning(request, f"{pending} upcoming appointment(s) still belong to {dentist.full_name}. "
#                                       "Reschedule or cancel them.")
#     return redirect("admin_dentists")

# @login_required
# def admin_dentists(request):
#     dentists = Dentist.objects.all()

#     context = {
#         'dentists': dentists
#     }
#     return render(request, 'clinic_admin/dentists.html', context)



# ------------------------------ |||| ---------------------------------

"""Staff-only dentist management: profile details, the linked user, and active/inactive status.
Put in the same app as models.py. Replaces your admin_dentists, admin_dentist_add / _edit / _delete views."""


User = get_user_model()


class DentistAdminForm(forms.ModelForm):
    class Meta:
        model = Dentist
        fields = ["full_name", "title", "specialization", "experience_years",
                  "qualifications", "bio", "photo", "is_active", "user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Offer accounts that are not linked to another dentist (plus this dentist's own account)
        available = Q(dentist_profile__isnull=True)
        if self.instance.pk:
            available |= Q(dentist_profile=self.instance)
        user_field = self.fields["user"]
        user_field.queryset = User.objects.filter(available).order_by("first_name", "username")
        user_field.required = False
        user_field.label = "User"
        user_field.empty_label = "No user"
        user_field.label_from_instance = lambda u: f"{u.get_full_name() or u.username} ({u.email or u.username})"

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        qs = Dentist.objects.filter(full_name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A dentist with this name already exists.")
        return name

    def clean_experience_years(self):
        years = self.cleaned_data.get("experience_years")
        if years is not None and years > 80:
            raise ValidationError("Enter a realistic number of years.")
        return years

    @transaction.atomic
    def save(self, commit=True):
        dentist = super().save(commit=False)
        dentist.save()                       # saves the photo too
        return dentist


def _flash_errors(request, form):
    for field, errors in form.errors.items():
        label = "" if field == "__all__" else form[field].label
        for error in errors:
            messages.error(request, f"{label}: {error}" if label else str(error))


# @staff_required
def admin_dentists(request):
    dentists = Dentist.objects.select_related("user").order_by("-is_active", "full_name")
    users = User.objects.select_related("dentist_profile").order_by("first_name", "username")
    return render(request, "clinic_admin/dentists.html", {"dentists": dentists, "users": users})


# @staff_required
@require_POST
def admin_dentists_add(request):
    form = DentistAdminForm(request.POST, request.FILES)
    if form.is_valid():
        dentist = form.save()
        messages.success(request, f"{dentist.full_name} was added.")
    else:
        _flash_errors(request, form)
    return redirect("admin_dentists")


# @staff_required
@require_POST
def admin_dentist_edit(request, pk):
    dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
    form = DentistAdminForm(request.POST, request.FILES, instance=dentist)
    if form.is_valid():
        dentist = form.save()
        messages.success(request, f"{dentist.full_name} was updated.")
    else:
        _flash_errors(request, form)
    return redirect("admin_dentists")


# @staff_required
@require_POST
def admin_dentist_toggle(request, pk):
    dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
    dentist.is_active = not dentist.is_active
    dentist.save(update_fields=["is_active"])
    if dentist.is_active:
        messages.success(request, f"{dentist.full_name} is now active.")
    else:
        pending = Appointment.objects.filter(
            dentist=dentist, status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            date__gte=timezone.localdate()).count()
        messages.success(request, f"{dentist.full_name} is now inactive.")
        if pending:
            messages.warning(request, f"{pending} upcoming appointment(s) still belong to {dentist.full_name}. "
                                      "Reschedule or cancel them.")
    return redirect("admin_dentists")


@staff_required
@require_POST
def admin_dentist_delete(request, pk):
    dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
    name = dentist.full_name
    try:
        dentist.delete()
    except ProtectedError:
        messages.error(request, f"{name} has appointment records and cannot be deleted. Deactivate them instead.")
    else:
        messages.success(request, f"{name} was deleted.")
    return redirect("admin_dentists")


@login_required
def admin_schedules(request):
    if request.method == 'GET':
        dentists = Dentist.objects.all()

        context = {
            'dentists': dentists
        }
    return render(request, 'clinic_admin/schedules.html', context)

@login_required
def admin_services(request):
    services = Service.objects.all()
    context = {
        'services': services
    }
    return render(request, 'clinic_admin/services.html', context)

@login_required
def admin_service_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        icon = request.POST.get('icon', '')
        short_description = request.POST.get('short_description', '')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')

        Service.objects.create(
            name = name,
            icon = icon,
            short_description = short_description,
            description = description,
            image = image
        )
        messages.success(request, 'service published succesfully')
    return render(request, 'clinic_admin/services.html')

# @staff_member_required
# @require_POST
def admin_service_toggle(request, pk):
    service = get_object_or_404(Service, pk=pk)

    service.is_published = not service.is_published
    service.save(update_fields=['is_published'])

    if service.is_published:
        messages.success(request, 'Service published successfully.')
    else:
        messages.success(request, 'Service unpublished successfully.')

    return redirect('admin_services')

# @staff_member_required
# @require_POST
def admin_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)

    service.delete()

    messages.success(request, 'Service deleted successfully.')

    return redirect('admin_services')


# @staff_member_required
def admin_service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)

    if request.method == 'POST':
        service.name = request.POST.get('name', '').strip()
        service.description = request.POST.get('description', '').strip()
        service.price = request.POST.get('price', '').strip()

        service.save()

        messages.success(request, 'Service updated successfully.')
        return redirect('admin_services')

    return render(request, 'clinic_admin/service_edit.html', {
        'service': service
    })

@login_required
def admin_settings(request):
    return render(request, 'clinic_admin/settings.html')

@login_required
def admin_testimonials(request):
    return render(request, 'clinic_admin/testimonials.html')

@login_required
def admin_blog(request):
    return render(request, 'clinic_admin/blog.html')

@login_required
def admin_blog_add(request):
    return render(request, 'clinic_admin/blog.html')

def doctor_sidebar(request):
    return render(request, 'partials/doctor_sidebar.html')



Status = Appointment.Status
ACTIVE = (Status.PENDING, Status.CONFIRMED)
SCOPES = ("upcoming", "past", "cancelled", "all")


def _parse_date(value, default):
    """?date=YYYY-MM-DD, falling back to default for anything invalid or absurd."""
    try:
        parsed = datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return default
    return parsed if 2000 <= parsed.year <= 2100 else default


def _safe_back(request, fallback):
    ref = request.META.get("HTTP_REFERER", "")
    if ref and url_has_allowed_host_and_scheme(
        ref, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(ref)
    return redirect(fallback)


# @doctor_required
def doctor_schedule(request):
    dentist = get_object_or_404(
        Dentist,
        user=request.user
    )
    today = timezone.localdate()
    day = _parse_date(request.GET.get("date"), today)

    mine = Appointment.objects.filter(dentist=dentist).exclude(status=Status.CANCELLED)
    appointments = list(mine.filter(date=day).select_related("service").order_by("time"))

    week_start = day - datetime.timedelta(days=day.weekday())      # Monday of the selected week
    week_end = week_start + datetime.timedelta(days=6)
    counts = dict(
        mine.filter(date__range=(week_start, week_end))
        .order_by().values_list("date").annotate(n=Count("id"))
    )
    week_days = []
    for i in range(7):
        d = week_start + datetime.timedelta(days=i)
        week_days.append({"date": d, "count": counts.get(d, 0), "is_today": d == today, "is_selected": d == day})

    upcoming = mine.filter(status__in=ACTIVE, date__gte=today)
    stats = {
        "day_count": len(appointments),
        "pending": upcoming.filter(status=Status.PENDING).count(),
        "upcoming": upcoming.count(),
    }
    return render(request, "clinic_admin/doctor_schedule.html", {
        "dentist": dentist,
        "day": day,
        "is_today": day == today,
        "prev_day": day - datetime.timedelta(days=1),
        "next_day": day + datetime.timedelta(days=1),
        "week_days": week_days,
        "appointments": appointments,
        "stats": stats,
    })


# @doctor_required
def doctor_appointments(request):
    dentist = get_object_or_404(
        Dentist,
        user=request.user
    )
    today = timezone.localdate()
    scope = request.GET.get("scope", "upcoming")
    if scope not in SCOPES:
        scope = "upcoming"

    qs = Appointment.objects.filter(dentist=dentist).select_related("service")
    if scope == "upcoming":
        qs = qs.filter(status__in=ACTIVE, date__gte=today).order_by("date", "time")
    elif scope == "past":
        qs = (qs.exclude(status=Status.CANCELLED)
                .filter(Q(status=Status.COMPLETED) | Q(date__lt=today))
                .order_by("-date", "-time"))
    elif scope == "cancelled":
        qs = qs.filter(status=Status.CANCELLED).order_by("-date", "-time")
    else:
        qs = qs.order_by("-date", "-time")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(service__name__icontains=q))

    page_obj = Paginator(qs, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    query_string = ("&" + params.urlencode()) if params else ""

    return render(request, "clinic_admin/doctor_appointments.html", {
        "dentist": dentist, "page_obj": page_obj, "scope": scope, "q": q, "query_string": query_string,
    })


# @doctor_required
@require_POST
def doctor_appointment_complete(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, dentist=request.dentist)   # 404 for anyone else's
    if not appointment.can_complete:
        messages.error(request, "This appointment can only be marked completed once it is confirmed and has started.")
    else:
        appointment.status = Status.COMPLETED
        appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Marked {appointment.full_name}'s appointment as completed.")
    return _safe_back(request, "doctor_schedule")