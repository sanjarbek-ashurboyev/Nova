import secrets

from django.contrib.auth.models import PermissionsMixin, AbstractUser, UserManager
from django.db.models import CharField, Model, ForeignKey, CASCADE, BigIntegerField, TextField, SET_NULL, \
    DecimalField
from django.db.models.enums import TextChoices

from accounts.phone import mask_phone


class CustomUserManager(UserManager):
    def create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Telefon raqam kiriting!")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser is_staff=True bo'lishi kerak.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser is_superuser=True bo'lishi kerak.")

        return self.create_user(phone, password, **extra_fields)

class Region(Model):
    title = CharField(max_length=50)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

class District(Model):
    title = CharField(max_length=50)
    region = ForeignKey(Region, on_delete=CASCADE, related_name='districts')

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class User(AbstractUser, PermissionsMixin):
    class RoleChoices(TextChoices):
        USER = 'user', 'User'
        OPERATOR = 'operator', 'Operator'
        DRIVER = 'driver', 'Haydovchi'

    username = None
    phone = CharField(max_length=20, unique=True)
    role = CharField(choices=RoleChoices, default=RoleChoices.USER)
    telegram_id = BigIntegerField(null=True, blank=True)
    description = TextField(blank=True, default='')
    referrer = ForeignKey('User', on_delete=SET_NULL, related_name='referrals', null=True, blank=True)
    balance = DecimalField(max_digits=12, decimal_places=0, default=0)
    api_key = CharField(max_length=64, unique=True, blank=True, null=True)
    district = ForeignKey('accounts.District', on_delete=SET_NULL, null=True, blank=True,
                          related_name='users')

    objects = CustomUserManager()
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self.generate_api_key()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_api_key():
        return secrets.token_hex(16)

    @property
    def display_name(self):
        return self.get_full_name().strip() or mask_phone(self.phone) or 'Sotuvchi'

    def __str__(self):
        return self.phone
