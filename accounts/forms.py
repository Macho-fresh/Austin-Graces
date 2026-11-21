from django import forms
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import *
from django.utils import timezone

class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username=email).exists():
            raise ValidationError('This email is already registered')
        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data['password1']
        password2 = cleaned_data['password2']
        if password1  and password2:
            if password1 != password2:
                self.add_error('password2', 'Passwords do not match')
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error('password1', e)

        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            password=self.cleaned_data["password1"]
        )

        return user

class AppointmentForm(forms.ModelForm):

    class Meta:
        model = Appointment
        fields = [
            'full_name',
            'email',
            'phone',
            'service',
            'dentist',
            'date',
            'time',
            'message',
        ]

        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['service'].queryset = Service.objects.filter(
            is_published=True
        ).order_by('name')

        self.fields['dentist'].queryset = Dentist.objects.filter(
            is_active=True
        ).order_by('full_name')

    def clean_date(self):
        appointment_date = self.cleaned_data['date']

        if appointment_date < timezone.localdate():
            raise forms.ValidationError(
                'Please choose today or a future date.'
            )

        return appointment_date