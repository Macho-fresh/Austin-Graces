from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Service)

@admin.register(Dentist)
class DentistAdmin(admin.ModelAdmin):
    list_display = ("full_name", "title", "user", "is_active")
    raw_id_fields = ("user",)
    search_fields = ("full_name", "user__username", "user__email")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "service", "dentist", "date", "time", "status")
    list_filter = ("status", "service", "dentist", "date")
    search_fields = ("full_name", "email", "phone")