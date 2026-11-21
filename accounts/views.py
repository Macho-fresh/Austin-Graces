from django.shortcuts import render, redirect
from .models import *
from django.contrib.auth import authenticate, login as auth_login
from .forms import *
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
import datetime
from datetime import date, datetime, time, timedelta
from django.contrib.auth.forms import AuthenticationForm
from django.utils.dateparse import parse_date
from django.db import transaction
from django.db import IntegrityError
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
import bleach
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
from django.views.decorators.http import require_http_methods
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

def get_available_slots(dentist, appointment_date):

    schedule = DentistSchedule.objects.filter(
        dentist=dentist,
        weekday=appointment_date.weekday(),
        is_working=True
    ).first()

    if not schedule:
        return []

    if not schedule.open_time or not schedule.close_time:
        return []

    slot_duration = schedule.slot_minutes

    if slot_duration <= 0:
        return []

    start = datetime.combine(
        appointment_date,
        schedule.open_time
    )

    closing = datetime.combine(
        appointment_date,
        schedule.close_time
    )

    booked_times = set(
        Appointment.objects.filter(
            dentist=dentist,
            date=appointment_date,
            status__in=['pending', 'confirmed']
        ).values_list('time', flat=True)
    )

    slots = []
    current = start

    now = timezone.localtime()

    while current + timedelta(minutes=slot_duration) <= closing:

        slot_time = current.time()

        # Don't offer times that have already passed today
        if appointment_date == now.date() and current <= now.replace(tzinfo=None):
            current += timedelta(minutes=slot_duration)
            continue

        # Don't offer already booked times
        if slot_time not in booked_times:
            slots.append({
                'value': slot_time.strftime('%H:%M'),
                'label': current.strftime('%I:%M %p').lstrip('0'),
            })

        current += timedelta(minutes=slot_duration)

    return slots

@login_required
def appointment(request):

    services = Service.objects.filter(
        is_published=True
    ).order_by('name')

    dentists = Dentist.objects.filter(
        is_active=True
    ).order_by('full_name')

    booking_success = False
    booking = None
    available_slots = []

    selected_service = request.GET.get('service', '')
    selected_dentist = request.GET.get('dentist', '')

    if request.method == 'POST':

        form = AppointmentForm(request.POST)

        if form.is_valid():

            dentist = form.cleaned_data['dentist']
            appointment_date = form.cleaned_data['date']
            appointment_time = form.cleaned_data['time']

            # Check that the selected time is still available
            available_slots = get_available_slots(
                dentist,
                appointment_date
            )

            valid_times = [
                slot['value'] for slot in available_slots
            ]

            if appointment_time.strftime('%H:%M') not in valid_times:

                form.add_error(
                    'time',
                    'This time slot is no longer available. Please choose another time.'
                )

            else:
                booking = form.save(commit=False)
                booking.status = 'pending'
                booking.save()

                booking_success = True

                messages.success(
                    request,
                    'Your appointment request has been received.'
                )

        if not booking_success:
            selected_service = ''
            selected_dentist = ''

            if form.is_bound:
                service_value = form['service'].value()
                dentist_value = form['dentist'].value()

                if service_value:
                    selected_service = get_object_or_404(
                        Service,
                        pk=service_value
                    ).slug

                if dentist_value:
                    selected_dentist = get_object_or_404(
                        Dentist,
                        pk=dentist_value
                    ).slug

                appointment_date = form['date'].value()

                if dentist_value and appointment_date:
                    parsed_date = parse_date(appointment_date)

                    if parsed_date:
                        selected_dentist_obj = get_object_or_404(
                            Dentist,
                            pk=dentist_value
                        )

                        available_slots = get_available_slots(
                            selected_dentist_obj,
                            parsed_date
                        )

    else:
        initial = {}

        if selected_service:
            service = services.filter(slug=selected_service).first()

            if service:
                initial['service'] = service

        if selected_dentist:
            dentist = dentists.filter(slug=selected_dentist).first()

            if dentist:
                initial['dentist'] = dentist

        form = AppointmentForm(initial=initial)

    context = {
        'form': form,
        'services': services,
        'dentists': dentists,
        'available_slots': available_slots,
        'booking_success': booking_success,
        'booking': booking,
        'selected_service': selected_service,
        'selected_dentist': selected_dentist,
    }

    return render(
        request,
        'appointment.html',
        context
    )

@login_required
@require_GET
def appointment_slots(request):

    dentist_id = request.GET.get('dentist')
    date_value = request.GET.get('date')

    if not dentist_id or not date_value:
        return JsonResponse({'slots': []})

    appointment_date = parse_date(date_value)

    if not appointment_date:
        return JsonResponse({'slots': []}, status=400)

    if appointment_date < timezone.localdate():
        return JsonResponse({'slots': []})

    dentist = get_object_or_404(
        Dentist,
        pk=dentist_id,
        is_active=True
    )

    slots = get_available_slots(dentist, appointment_date)

    return JsonResponse({
        'slots': slots
    })

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
    today = timezone.localdate()
    now = timezone.localtime()

    # Appointment statistics
    stats = {
        'total': Appointment.objects.count(),

        'pending': Appointment.objects.filter(
            status='pending'
        ).count(),

        'confirmed': Appointment.objects.filter(
            status='confirmed'
        ).count(),

        'completed': Appointment.objects.filter(
            status='completed'
        ).count(),

        'patients': User.objects.filter(
            is_staff=False,
            is_superuser=False,
            dentist_profile__isnull=True
        ).count(),
    }

    # Recent appointments
    recent_appointments = (
        Appointment.objects
        .select_related('service', 'dentist')
        .annotate(patient_name=F('full_name'))
        .order_by('-updated_at')[:5]
    )

    # Upcoming appointments
    upcoming_appointments = (
        Appointment.objects
        .select_related('service', 'dentist')
        .annotate(patient_name=F('full_name'))
        .filter(
            Q(date__gt=today) |
            Q(date=today, time__gte=now.time()),
            status__in=['pending', 'confirmed']
        )
        .order_by('date', 'time')[:5]
    )

    # Weekly chart data: Monday to Sunday
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Monthly chart data: last 30 days
    month_start = today - timedelta(days=29)

    def get_chart_data(start_date, end_date):
        dates = [
            start_date + timedelta(days=i)
            for i in range((end_date - start_date).days + 1)
        ]

        results = (
            Appointment.objects
            .filter(date__range=[start_date, end_date])
            .values('date', 'status')
            .annotate(total=Count('pk'))
        )

        daily_counts = {
            day: {
                'pending': 0,
                'confirmed': 0,
                'completed': 0,
            }
            for day in dates
        }

        for item in results:
            status = item['status']

            if status in daily_counts[item['date']]:
                daily_counts[item['date']][status] = item['total']

        return {
            'labels': [day.strftime('%a %d') for day in dates],
            'pending': [
                daily_counts[day]['pending'] for day in dates
            ],
            'confirmed': [
                daily_counts[day]['confirmed'] for day in dates
            ],
            'completed': [
                daily_counts[day]['completed'] for day in dates
            ],
        }

    chart_data = {
        'week': get_chart_data(week_start, week_end),
        'month': get_chart_data(month_start, today),
    }

    # Recent activity based on recently updated appointments
    activities = []

    for appointment in recent_appointments:
        activities.append({
            'text': (
                f"Appointment from {appointment.full_name} "
                f"was updated to {appointment.get_status_display()}."
            ),
            'created_at': appointment.updated_at,
        })

    context = {
        'stats': stats,
        'recent_appointments': recent_appointments,
        'upcoming_appointments': upcoming_appointments,
        'activities': activities,
        'chart_data': chart_data,
        'notifications': [],
    }

    return render(
        request,
        'clinic_admin/dashboard.html',
        context
    )

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

    patients = User.objects.filter(
        dentist_profile__isnull=True,
        is_staff=False,
        is_superuser=False
    ).prefetch_related(
        'appointments'
    ).order_by('-date_joined')

    paginator = Paginator(patients, 10)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
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

# ------------------------------ |||| ---------------------------------

# """Staff-only dentist management: profile details, the linked user, and active/inactive status.
# Put in the same app as models.py. Replaces your admin_dentists, admin_dentist_add / _edit / _delete views."""


# User = get_user_model()


# class DentistAdminForm(forms.ModelForm):
#     class Meta:
#         model = Dentist
#         fields = ["full_name", "title", "specialization", "experience_years",
#                   "qualifications", "bio", "photo", "is_active", "user"]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Offer accounts that are not linked to another dentist (plus this dentist's own account)
#         available = Q(dentist_profile__isnull=True)
#         if self.instance.pk:
#             available |= Q(dentist_profile=self.instance)
#         user_field = self.fields["user"]
#         user_field.queryset = User.objects.filter(available).order_by("first_name", "username")
#         user_field.required = False
#         user_field.label = "User"
#         user_field.empty_label = "No user"
#         user_field.label_from_instance = lambda u: f"{u.get_full_name() or u.username} ({u.email or u.username})"

#     def clean_full_name(self):
#         name = self.cleaned_data["full_name"].strip()
#         qs = Dentist.objects.filter(full_name__iexact=name)
#         if self.instance.pk:
#             qs = qs.exclude(pk=self.instance.pk)
#         if qs.exists():
#             raise ValidationError("A dentist with this name already exists.")
#         return name

#     def clean_experience_years(self):
#         years = self.cleaned_data.get("experience_years")
#         if years is not None and years > 80:
#             raise ValidationError("Enter a realistic number of years.")
#         return years

#     @transaction.atomic
#     def save(self, commit=True):
#         dentist = super().save(commit=False)
#         dentist.save()                       # saves the photo too
#         return dentist


# def _flash_errors(request, form):
#     for field, errors in form.errors.items():
#         label = "" if field == "__all__" else form[field].label
#         for error in errors:
#             messages.error(request, f"{label}: {error}" if label else str(error))


# # @staff_required
# def admin_dentists(request):
#     dentists = Dentist.objects.select_related("user").order_by("-is_active", "full_name")
#     users = User.objects.select_related("dentist_profile").order_by("first_name", "username")
#     return render(request, "clinic_admin/dentists.html", {"dentists": dentists, "users": users})


# # @staff_required
# @require_POST
# def admin_dentists_add(request):
#     form = DentistAdminForm(request.POST, request.FILES)
#     if form.is_valid():
#         dentist = form.save()
#         messages.success(request, f"{dentist.full_name} was added.")
#     else:
#         _flash_errors(request, form)
#     return redirect("admin_dentists")


# # @staff_required
# @require_POST
# def admin_dentist_edit(request, pk):
#     dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
#     form = DentistAdminForm(request.POST, request.FILES, instance=dentist)
#     if form.is_valid():
#         dentist = form.save()
#         messages.success(request, f"{dentist.full_name} was updated.")
#     else:
#         _flash_errors(request, form)
#     return redirect("admin_dentists")


# # @staff_required
# @require_POST
# def admin_dentist_toggle(request, pk):
#     dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
#     dentist.is_active = not dentist.is_active
#     dentist.save(update_fields=["is_active"])
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


# @staff_required
# @require_POST
# def admin_dentist_delete(request, pk):
#     dentist = get_object_or_404(Dentist.objects.select_related("user"), pk=pk)
#     name = dentist.full_name
#     try:
#         dentist.delete()
#     except ProtectedError:
#         messages.error(request, f"{name} has appointment records and cannot be deleted. Deactivate them instead.")
#     else:
#         messages.success(request, f"{name} was deleted.")
#     return redirect("admin_dentists")


@login_required
def admin_dentists(request):
    dentists = Dentist.objects.select_related(
        'user'
    ).all().order_by('full_name')

    users = User.objects.select_related(
        'dentist_profile'
    ).all().order_by('first_name')

    context = {
        'dentists': dentists,
        'users': users,
    }

    return render(request, 'clinic_admin/dentists.html', context)

def get_dentist_form_data(request, dentist=None):
    full_name = request.POST.get('full_name', '').strip()
    title = request.POST.get('title', '').strip()
    specialization = request.POST.get('specialization', '').strip()
    qualifications = request.POST.get('qualifications', '').strip()
    bio = request.POST.get('bio', '').strip()

    experience = request.POST.get('experience_years', '').strip()
    user_id = request.POST.get('user', '').strip()

    is_active = request.POST.get('is_active') == 'true'

    if not full_name or not title:
        return None, 'Full name and professional title are required.'

    experience_years = None

    if experience:
        try:
            experience_years = int(experience)

            if not 0 <= experience_years <= 80:
                return None, 'Experience must be between 0 and 80 years.'

        except ValueError:
            return None, 'Enter a valid number of years of experience.'

    linked_user = None

    if user_id:
        linked_user = get_object_or_404(User, pk=user_id)

        existing = Dentist.objects.filter(
            user=linked_user
        )

        if dentist:
            existing = existing.exclude(pk=dentist.pk)

        if existing.exists():
            return None, 'This user is already linked to another dentist.'

    data = {
        'full_name': full_name,
        'title': title,
        'specialization': specialization,
        'qualifications': qualifications,
        'bio': bio,
        'experience_years': experience_years,
        'is_active': is_active,
        'user': linked_user,
    }

    return data, None

@login_required
@require_POST
def admin_dentists_add(request):
    data, error = get_dentist_form_data(request)

    if error:
        messages.error(request, error)
        return redirect('admin_dentists')

    dentist = Dentist(**data)

    if request.FILES.get('photo'):
        dentist.photo = request.FILES['photo']

    try:
        dentist.save()
        messages.success(request, f'{dentist.full_name} added successfully.')

    except IntegrityError:
        messages.error(request, 'This user is already assigned to another dentist.')

    return redirect('admin_dentists')

@login_required
@require_POST
def admin_dentist_edit(request, pk):
    dentist = get_object_or_404(Dentist, pk=pk)

    data, error = get_dentist_form_data(request, dentist)

    if error:
        messages.error(request, error)
        return redirect('admin_dentists')

    for field, value in data.items():
        setattr(dentist, field, value)

    if request.FILES.get('photo'):
        dentist.photo = request.FILES['photo']

    try:
        dentist.save()
        messages.success(request, f'{dentist.full_name} updated successfully.')

    except IntegrityError:
        messages.error(request, 'This user is already assigned to another dentist.')

    return redirect('admin_dentists')

@login_required
@require_POST
def admin_dentist_toggle(request, pk):
    dentist = get_object_or_404(Dentist, pk=pk)

    dentist.is_active = not dentist.is_active
    dentist.save(update_fields=['is_active'])

    if dentist.is_active:
        messages.success(request, f'{dentist.full_name} activated successfully.')
    else:
        messages.success(request, f'{dentist.full_name} deactivated successfully.')

    return redirect('admin_dentists')

@login_required
@require_POST
def admin_dentist_delete(request, pk):
    dentist = get_object_or_404(Dentist, pk=pk)

    if Appointment.objects.filter(dentist=dentist).exists():
        messages.error(
            request,
            'This dentist has appointment records and cannot be deleted. Deactivate them instead.'
        )
        return redirect('admin_dentists')

    name = dentist.full_name
    dentist.delete()

    messages.success(request, f'{name} deleted successfully.')

    return redirect('admin_dentists')

@login_required
def admin_schedules(request):
    dentists = Dentist.objects.all().order_by('full_name')

    dentist_id = request.GET.get('dentist')

    selected_dentist = None

    if dentist_id:
        selected_dentist = dentists.filter(pk=dentist_id).first()

    if not selected_dentist:
        selected_dentist = dentists.first()

    context = {
        'dentists': dentists,
        'selected_dentist': selected_dentist,
        'schedule_days': [],
        'week_days': [],
        'slot_minutes': 30,
    }

    if not selected_dentist:
        return render(request, 'clinic_admin/schedules.html', context)

    # Retrieve existing schedules
    schedules = {
        schedule.weekday: schedule
        for schedule in DentistSchedule.objects.filter(
            dentist=selected_dentist
        )
    }

    schedule_days = []

    for index in range(7):
        schedule = schedules.get(index)

        schedule_days.append({
            'index': index,
            'name': date(2024, 1, 1).replace(
                day=1
            ).strftime('%A') if False else [
                'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday'
            ][index],
            'is_working': schedule.is_working if schedule else False,
            'open_time': schedule.open_time if schedule else None,
            'close_time': schedule.close_time if schedule else None,
        })

    # Get appointment duration
    existing_schedule = next(iter(schedules.values()), None)

    slot_minutes = existing_schedule.slot_minutes if existing_schedule else 30

    # Get the current week's Monday
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())

    week_days = []

    for index in range(7):
        current_date = monday + timedelta(days=index)
        schedule = schedules.get(index)

        entries = []

        if schedule and schedule.is_working and schedule.open_time and schedule.close_time:

            # Retrieve appointments for this dentist on this date
            appointments = Appointment.objects.filter(
                dentist=selected_dentist,
                date=current_date,
            ).exclude(status='cancelled')

            booked_times = {
                appointment.time: appointment
                for appointment in appointments
            }

            # Generate appointment slots
            current_time = datetime.combine(
                current_date,
                schedule.open_time
            )

            closing_time = datetime.combine(
                current_date,
                schedule.close_time
            )

            while current_time + timedelta(minutes=slot_minutes) <= closing_time:

                slot_time = current_time.time()

                appointment = booked_times.get(slot_time)

                if appointment:
                    patient = getattr(appointment, 'patient', None)

                    if patient:
                        patient_name = (
                            patient.get_full_name()
                            or getattr(patient, 'full_name', str(patient))
                        )
                    else:
                        patient_name = 'Patient'

                    entries.append({
                        'time': slot_time,
                        'patient': patient_name,
                        'service': appointment.service,
                        'free': False,
                    })

                else:
                    entries.append({
                        'time': slot_time,
                        'patient': '',
                        'service': '',
                        'free': True,
                    })

                current_time += timedelta(minutes=slot_minutes)

        week_days.append({
            'label': current_date.strftime('%A'),
            'date': current_date,
            'is_working': schedule.is_working if schedule else False,
            'entries': entries,
        })

    context.update({
        'schedule_days': schedule_days,
        'week_days': week_days,
        'slot_minutes': slot_minutes,
        'week_label': f'{monday.strftime("%d %b")} - {(monday + timedelta(days=6)).strftime("%d %b %Y")}',
    })

    return render(request, 'clinic_admin/schedules.html', context)


@login_required
def admin_schedule_save(request):

    if request.method != 'POST':
        return redirect('admin_schedules')

    dentist_id = request.POST.get('dentist')

    dentist = get_object_or_404(Dentist, pk=dentist_id)

    try:
        slot_minutes = int(request.POST.get('slot_minutes', 30))

        if slot_minutes not in [15, 30, 45, 60]:
            messages.error(request, 'Invalid appointment duration.')
            return redirect('admin_schedules')

        for index in range(7):

            is_working = request.POST.get(f'work_{index}') == '1'

            open_time = request.POST.get(f'open_{index}')
            close_time = request.POST.get(f'close_{index}')

            if is_working:

                if not open_time or not close_time:
                    messages.error(
                        request,
                        'Opening and closing times are required for working days.'
                    )
                    return redirect(
                        f'/admin/schedules/?dentist={dentist.pk}'
                    )

                opening = time.fromisoformat(open_time)
                closing = time.fromisoformat(close_time)

                if opening >= closing:
                    messages.error(
                        request,
                        'Closing time must be later than opening time.'
                    )
                    return redirect(
                        f'/admin/schedules/?dentist={dentist.pk}'
                    )

            else:
                opening = None
                closing = None

            DentistSchedule.objects.update_or_create(
                dentist=dentist,
                weekday=index,
                defaults={
                    'is_working': is_working,
                    'open_time': opening,
                    'close_time': closing,
                    'slot_minutes': slot_minutes,
                }
            )

        messages.success(
            request,
            f'Schedule for {dentist.full_name} saved successfully.'
        )

    except (ValueError, TypeError):
        messages.error(request, 'Invalid schedule information.')

    return redirect(f'/admin/schedules/?dentist={dentist.pk}')

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
@require_http_methods(["GET", "POST"])
def admin_settings(request):

    # Get the existing settings or create them
    settings, created = ClinicSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':

        clinic_name = request.POST.get('clinic_name', '').strip()
        tagline = request.POST.get('tagline', '').strip()
        about_summary = request.POST.get('about_summary', '').strip()

        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        address = request.POST.get('address', '').strip()
        map_embed_url = request.POST.get('map_embed_url', '').strip()

        facebook_url = request.POST.get('facebook_url', '').strip()
        instagram_url = request.POST.get('instagram_url', '').strip()
        x_url = request.POST.get('x_url', '').strip()

        booking_enabled = request.POST.get('booking_enabled') == '1'

        # Validate required field
        if not clinic_name:
            messages.error(request, 'Clinic name is required.')
            return redirect('admin_settings')

        # Handle opening hours
        hours_days = request.POST.getlist('hours_days')
        hours_text = request.POST.getlist('hours_text')

        opening_hours = []

        for days, hours in zip(hours_days, hours_text):
            days = days.strip()
            hours = hours.strip()

            if days and hours:
                opening_hours.append({
                    'days': days,
                    'hours': hours,
                })

        # Update settings
        settings.clinic_name = clinic_name
        settings.tagline = tagline
        settings.about_summary = about_summary

        settings.phone = phone
        settings.email = email
        settings.whatsapp = whatsapp
        settings.address = address
        settings.map_embed_url = map_embed_url

        settings.facebook_url = facebook_url
        settings.instagram_url = instagram_url
        settings.x_url = x_url

        settings.booking_enabled = booking_enabled
        settings.opening_hours = opening_hours

        # Only update logo if a new one was uploaded
        logo = request.FILES.get('logo')

        if logo:
            settings.logo = logo

        settings.save()

        messages.success(request, 'Website settings saved successfully.')
        return redirect('admin_settings')

    return render(request, 'clinic_admin/settings.html', {
        'settings': settings,
    })

@login_required
def admin_testimonials(request):

    testimonials = Testimonial.objects.all().order_by('-created_at')

    paginator = Paginator(testimonials, 10)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }

    return render(request, 'clinic_admin/testimonials.html', context)


@login_required
@require_POST
def admin_testimonial_toggle(request, pk):

    testimonial = get_object_or_404(Testimonial, pk=pk)

    testimonial.is_published = not testimonial.is_published

    testimonial.save(update_fields=['is_published'])

    if testimonial.is_published:
        messages.success(
            request,
            'Testimonial published successfully.'
        )
    else:
        messages.success(
            request,
            'Testimonial unpublished successfully.'
        )

    return redirect('admin_testimonials')

@login_required
@require_POST
def admin_testimonial_delete(request, pk):

    testimonial = get_object_or_404(Testimonial, pk=pk)

    testimonial.delete()

    messages.success(
        request,
        'Testimonial deleted successfully.'
    )

    return redirect('admin_testimonials')

@login_required
def admin_blog(request):
    posts = BlogPost.objects.select_related('category').all().order_by('-created_at')

    categories = BlogCategory.objects.all().order_by('name')

    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clinic_admin/blog.html', {
        'page_obj': page_obj,
        'categories': categories,
    })

@login_required
@require_POST
def admin_blog_add(request):
    title = request.POST.get('title', '').strip()
    category_id = request.POST.get('category', '').strip()
    excerpt = request.POST.get('excerpt', '').strip()
    content = request.POST.get('content', '').strip()

    is_published = request.POST.get('is_published') == 'true'
    is_featured = request.POST.get('is_featured') == 'true'

    image = request.FILES.get('image')

    if not title or not content:
        messages.error(request, 'Title and content are required.')
        return redirect('admin_blog')

    category = None

    if category_id:
        category = get_object_or_404(BlogCategory, pk=category_id)

    # Generate a unique slug
    base_slug = slugify(title)
    slug = base_slug
    counter = 1

    while BlogPost.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    # Sanitise HTML content before saving
    clean_content = bleach.clean(
        content,
        tags=[
            'p', 'br', 'strong', 'b', 'em', 'i',
            'u', 'h1', 'h2', 'h3', 'h4',
            'ul', 'ol', 'li', 'blockquote',
            'a', 'img', 'pre', 'code',
        ],
        attributes={
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height'],
        },
        protocols=['http', 'https', 'mailto'],
        strip=True
    )

    post = BlogPost.objects.create(
        title=title,
        slug=slug,
        category=category,
        excerpt=excerpt,
        content=clean_content,
        image=image,
        is_published=is_published,
        is_featured=is_featured,
        published_at=timezone.now() if is_published else None,
    )

    messages.success(request, 'Article added successfully.')
    return redirect('admin_blog')

@login_required
@require_POST
def admin_blog_edit(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)

    title = request.POST.get('title', '').strip()
    category_id = request.POST.get('category', '').strip()
    excerpt = request.POST.get('excerpt', '').strip()
    content = request.POST.get('content', '').strip()

    is_published = request.POST.get('is_published') == 'true'
    is_featured = request.POST.get('is_featured') == 'true'

    image = request.FILES.get('image')

    if not title or not content:
        messages.error(request, 'Title and content are required.')
        return redirect('admin_blog')

    category = None

    if category_id:
        category = get_object_or_404(BlogCategory, pk=category_id)

    # Regenerate slug only if the title has changed
    if title != post.title:
        base_slug = slugify(title)
        slug = base_slug
        counter = 1

        while BlogPost.objects.filter(slug=slug).exclude(pk=post.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        post.slug = slug

    clean_content = bleach.clean(
        content,
        tags=[
            'p', 'br', 'strong', 'b', 'em', 'i',
            'u', 'h1', 'h2', 'h3', 'h4',
            'ul', 'ol', 'li', 'blockquote',
            'a', 'img', 'pre', 'code',
        ],
        attributes={
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height'],
        },
        protocols=['http', 'https', 'mailto'],
        strip=True
    )

    post.title = title
    post.category = category
    post.excerpt = excerpt
    post.content = clean_content
    post.is_published = is_published
    post.is_featured = is_featured

    # Only replace the existing image if a new one was uploaded
    if image:
        post.image = image

    # Set publication date the first time the article is published
    if is_published and not post.published_at:
        post.published_at = timezone.now()

    post.save()

    messages.success(request, 'Article updated successfully.')
    return redirect('admin_blog')

@login_required
@require_POST
def admin_blog_toggle(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)

    post.is_published = not post.is_published

    if post.is_published and not post.published_at:
        post.published_at = timezone.now()

    post.save(update_fields=['is_published', 'published_at'])

    if post.is_published:
        messages.success(request, 'Article published successfully.')
    else:
        messages.success(request, 'Article unpublished successfully.')

    return redirect('admin_blog')

@login_required
@require_POST
def admin_blog_delete(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)

    post.delete()

    messages.success(request, 'Article deleted successfully.')
    return redirect('admin_blog')

def doctor_sidebar(request):
    return render(request, 'partials/doctor_sidebar.html')



Status = Appointment.Status
ACTIVE = (Status.PENDING, Status.CONFIRMED)
SCOPES = ("upcoming", "past", "cancelled", "all")


def _parse_date(value, default):
    """?date=YYYY-MM-DD, falling back to default for anything invalid or absurd."""
    try:
        parsed = date.fromisoformat(value)
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

    week_start = day - timedelta(days=day.weekday())      # Monday of the selected week
    week_end = week_start + timedelta(days=6)
    counts = dict(
        mine.filter(date__range=(week_start, week_end))
        .order_by().values_list("date").annotate(n=Count("id"))
    )
    week_days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
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
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
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