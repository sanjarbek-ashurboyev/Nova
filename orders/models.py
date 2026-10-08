from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    F,
    FileField,
    ForeignKey,
    Model,
    OneToOneField,
    TextChoices,
)
from django.db.models.fields import (
    CharField,
    DateTimeField,
    DecimalField,
    PositiveSmallIntegerField,
    TextField,
)

from accounts.phone import phone_validator


class Order(Model):
    class OrderStatus(models.TextChoices):
        NEW = 'new', 'Yangi'
        PACKAGING = 'packaging', 'Qadoqlash'
        SHIPPING = 'shipping', 'Yetkazilmoqda'
        DELIVERED = 'delivered', 'Yetkazildi'
        PICKUP_LATER = 'pickup_later', 'Keyin oladi'
        RETURNED = 'returned', 'Qaytib keldi'
        CANCELLED = 'cancelled', 'Bekor qilindi'
        HOLD = 'hold', 'Hold'
        ARCHIVE = 'archive', 'Arxiv'

    product = ForeignKey('catalog.Product', on_delete=PROTECT, related_name='orders')
    customer_name = CharField(max_length=150)
    phone = CharField(max_length=20, validators=[phone_validator])
    quantity = PositiveSmallIntegerField(default=1)
    status = CharField(max_length=20, choices=OrderStatus, default=OrderStatus.NEW)
    user = ForeignKey('accounts.User', null=True, blank=True, on_delete=SET_NULL, related_name='orders')
    thread = ForeignKey('catalog.Thread', null=True, blank=True,
                               on_delete=SET_NULL, related_name='orders')
    operator = ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=SET_NULL,
        related_name='handled_orders', limit_choices_to={'role': 'operator'},
    )
    driver = ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=SET_NULL,
        related_name='deliveries', limit_choices_to={'role': 'driver'},
    )
    taken_at = DateTimeField(null=True, blank=True)
    delivered_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    district = ForeignKey('accounts.District', on_delete=SET_NULL, related_name='orders', null=True, blank=True)
    address = TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', 'operator']),
            models.Index(fields=['driver', 'status']),
        ]

    @property
    def total_price(self):
        unit_price = self.product.price - (self.thread.discount if self.thread else 0)
        return max(unit_price, 0) * self.quantity

    def __str__(self):
        return f"Order #{self.pk} — {self.customer_name}"


class Payment(Model):
    class Status(TextChoices):
        NEW = 'new', "Yangi"
        PAID = 'paid', "To'landi"
        CANCELLED = 'cancelled', "Bekor qilindi"

    card_number = CharField(max_length=16)
    amount = DecimalField(max_digits=12, decimal_places=0, default=0)
    created_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=20, choices=Status, default=Status.NEW)
    user = ForeignKey('accounts.User', on_delete=CASCADE, related_name='payments')
    receipt = FileField(
        "Chek", upload_to='receipts/', null=True, blank=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png', 'webp'])],
    )

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='new'),
                name='unique_pending_payment_per_user',
            )
        ]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_status = instance.status
        instance._loaded_amount = instance.amount
        return instance

    def save(self, *args, **kwargs):
        previous_status = getattr(self, '_loaded_status', None)
        previous_amount = getattr(self, '_loaded_amount', None)

        with transaction.atomic():
            super().save(*args, **kwargs)

            was_paid = previous_status == self.Status.PAID
            is_paid = self.status == self.Status.PAID

            if is_paid and not was_paid:
                delta = -self.amount
            elif was_paid and not is_paid:
                delta = previous_amount
            elif was_paid and is_paid and previous_amount != self.amount:
                delta = previous_amount - self.amount
            else:
                delta = 0

            if delta:
                User = get_user_model()
                User.objects.filter(pk=self.user_id).update(balance=F('balance') + delta)
                if 'user' in self._state.fields_cache:
                    self.user.refresh_from_db(fields=['balance'])

        self._loaded_status = self.status
        self._loaded_amount = self.amount

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} {self.amount} {self.status}"


class Survey(Model):
    order = OneToOneField('orders.Order', on_delete=CASCADE, related_name='survey')
    operator = ForeignKey('accounts.User', null=True, blank=True, on_delete=SET_NULL,
                          related_name='conducted_surveys', limit_choices_to={'role': 'operator'})
    comment = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Survey #{self.pk} — Order #{self.order_id}"
