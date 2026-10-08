from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import CharField, Form, ModelForm, PasswordInput

from accounts.phone import normalize_phone

User = get_user_model()


class RegisterForm(ModelForm):
    phone = CharField(max_length=30)
    password = CharField(widget=PasswordInput)
    password_confirm = CharField(widget=PasswordInput)

    class Meta:
        model = User
        fields = ['phone', 'first_name', 'last_name', 'password']

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data['phone'])
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan")
        return phone

    def clean_password(self):
        password = self.cleaned_data['password']
        probe = User(
            phone=self.cleaned_data.get('phone', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )
        validate_password(password, probe)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise ValidationError("Parollar mos kelmadi")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(Form):
    phone = CharField(max_length=30)
    password = CharField(widget=PasswordInput)

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

class UserUpdateModelForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'district', 'telegram_id', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('district', 'telegram_id', 'description'):
            self.fields[name].required = False


class UserPasswordUpdateForm(SetPasswordForm):
    error_messages = SetPasswordForm.error_messages | {
        'password_mismatch': "Parollar mos kelmadi",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Yangi parol'
        self.fields['new_password2'].label = 'Yangi parolni tasdiqlang'
