from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


class User(AbstractUser):
    email = models.EmailField()
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)


class Service(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Bootstrap Icons class, e.g. bi-heart-pulse")
    image = models.ImageField(upload_to="services/", blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Dentist(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="dentist_profile",
        help_text="Login account for this dentist. Leave empty if they do not log in.",
    )
    full_name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    title = models.CharField(max_length=120)
    specialization = models.CharField(max_length=120, blank=True)
    qualifications = models.TextField(blank=True, help_text="One per line")
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="dentists/", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.full_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    # Null for guests who book without an account
    patient = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="appointments")
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="appointments")
    dentist = models.ForeignKey(Dentist, on_delete=models.PROTECT, related_name="appointments")
    date = models.DateField()
    time = models.TimeField()
    message = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-time"]
        indexes = [models.Index(fields=["date", "status"])]
        constraints = [
            # One live booking per dentist per slot. Cancelled ones free the slot up.
            models.UniqueConstraint(
                fields=["dentist", "date", "time"],
                condition=Q(status__in=["pending", "confirmed"]),
                name="unique_active_slot",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.service} on {self.date} {self.time:%H:%M}"

    @property
    def patient_name(self):          # used by the admin templates
        return self.full_name

    @property
    def starts_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.date, self.time))

    @property
    def is_past(self):
        return self.starts_at < timezone.now()

    @property
    def can_cancel(self):            # used by the patient portal templates
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED) and not self.is_past

    @property
    def can_complete(self):
        """Confirmed and already started (used by the doctor 'Mark completed' button)."""
        return self.status == self.Status.CONFIRMED and self.starts_at <= timezone.now()

    def clean(self):
        if self._state.adding and self.date and self.time and self.is_past:
            raise ValidationError("Choose a date and time in the future.")

# models.py

class DentistSchedule(models.Model):
    DAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    dentist = models.ForeignKey(
        Dentist,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    weekday = models.PositiveSmallIntegerField(choices=DAYS)
    is_working = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    slot_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['weekday']
        constraints = [
            models.UniqueConstraint(
                fields=['dentist', 'weekday'],
                name='unique_dentist_weekday'
            )
        ]

    def __str__(self):
        return f'{self.dentist} - {self.get_weekday_display()}'