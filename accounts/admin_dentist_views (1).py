"""Staff-only dentist management: profile details, the linked user, and active/inactive status.
Put in the same app as models.py. Replaces your admin_dentists, admin_dentist_add / _edit / _delete views."""
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


@staff_required
def admin_dentists(request):
    dentists = Dentist.objects.select_related("user").order_by("-is_active", "full_name")
    users = User.objects.select_related("dentist_profile").order_by("first_name", "username")
    return render(request, "clinic_admin/dentists.html", {"dentists": dentists, "users": users})


@staff_required
@require_POST
def admin_dentist_add(request):
    form = DentistAdminForm(request.POST, request.FILES)
    if form.is_valid():
        dentist = form.save()
        messages.success(request, f"{dentist.full_name} was added.")
    else:
        _flash_errors(request, form)
    return redirect("admin_dentists")


@staff_required
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


@staff_required
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
