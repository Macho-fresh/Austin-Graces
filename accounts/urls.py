from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', home, name='home'),
    path('appointment/', appointment, name='appointment'),
    path('appointment_slots/', appointment_slots, name='appointment_slots'),
    path('services/', services, name='services'),
    path('about/', about, name='about'),
    path('dentists/', dentists, name='dentists'),
    path('testimonials/', testimonials, name='testimonials'),
    path('faq/', faq, name='faq'),
    path('contact/', contact, name='contact'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('blog/', blog, name='blog'),
    path('register/', register, name='register'),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="registration/ag_password_reset_form.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/ag_password_reset_done.html"), name="password_reset_done"),

    path(
        "password_reset_confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/ag_password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    path(
        "password_reset_complete/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/ag_password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),
    path('dashboard', dashboard, name='dashboard'),
    # path('password_reset_confirm', password_reset_confirm, name='password_reset_confirm'),
    path('my_appointments', my_appointments, name='my_appointments'),
    path('profile', profile, name='profile'),
    path('appointment', appointment, name='appointment'),
    path('password_change', password_change, name='password_change'),
    path('admin_dashboard', admin_dashboard, name='admin_dashboard'),
    path('admin_appointments', admin_appointments, name='admin_appointments'),
    path('admin_patients', admin_patients, name='admin_patients'),
    path('admin_dentist_add', admin_dentists_add, name='admin_dentist_add'),
    path('admin_dentists', admin_dentists, name='admin_dentists'),
    path('admin_schedules', admin_schedules, name='admin_schedules'),
    path('admin_services', admin_services, name='admin_services'),
    path('admin_service_add', admin_service_add, name='admin_service_add'),
    path('admin_settings', admin_settings, name='admin_settings'),
    path('admin_testimonials', admin_testimonials, name='admin_testimonials'),
    path('admin_blog', admin_blog, name='admin_blog'),
    path('admin_blog_add', admin_blog_add, name='admin_blog_add'),
    path(
    'admin_dentists/<int:pk>/edit/',
    admin_dentist_edit,
    name='admin_dentist_edit'
    ),
    path(
    'admin_dentists/<int:pk>/delete/',
    admin_dentist_delete,
    name='admin_dentist_delete'
    ),
    path("doctor/schedule/", doctor_schedule, name="doctor_schedule"),
    path("doctor/appointments/", doctor_appointments, name="doctor_appointments"),
    path("doctor/appointments/<int:pk>/complete/", doctor_appointment_complete, name="doctor_appointment_complete"),
    path("doctor_sidebar", doctor_sidebar, name="doctor_sidebar"),
    path(
    'admin_services/<int:pk>/toggle/',
    admin_service_toggle,
    name='admin_service_toggle'
    ),

    path(
        'admin/dentist/<int:pk>/toggle',
        admin_dentist_toggle,
        name='admin_dentist_toggle'
        ),

    path(
        'admin_services/<int:pk>/delete/',
        admin_service_delete,
        name='admin_service_delete'
    ),

    path(
    'admin_services/<int:pk>/edit/',
    admin_service_edit,
    name='admin_service_edit'
    ),

    path(
    'services/<slug:slug>/',
    service_detail,
    name='service_detail'
    ),

    path(
    'dentists/<slug:slug>/',
    dentist_detail,
    name='dentist_detail'
    ),
    path('admin/patients/<int:pk>/edit/', admin_patient_edit, name='admin_patient_edit'),
]

