from django.core.exceptions import ValidationError
from django.forms import CharField, IntegerField, ModelForm

from accounts.phone import normalize_phone
from orders.models import Order, Payment


class OrderCreateForm(ModelForm):
    fullname = CharField(max_length=255)
    phone_number = CharField(max_length=30)
    quantity = IntegerField(min_value=1)

    class Meta:
        model = Order
        fields = ['fullname', 'phone_number', 'quantity']

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    def clean_phone_number(self):
        return normalize_phone(self.cleaned_data['phone_number'])

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.product is not None and quantity > self.product.stock:
            raise ValidationError(
                f"Omborda faqat {max(self.product.stock, 0)} dona qoldi."
            )
        return quantity


class PaymentForm(ModelForm):
    class Meta:
        model = Payment
        fields = ['card_number', 'amount']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        if self.user and Payment.objects.filter(
                user=self.user, status=Payment.Status.NEW).exists():
            raise ValidationError(
                "Sizda ko'rib chiqilmagan to'lov so'rovi mavjud. "
                "Yangi so'rov yuborish uchun avvalgisi yakunlanishini kuting."
            )
        return cleaned

    def clean_card_number(self):
        card_number = self.cleaned_data['card_number']

        if not card_number.isdigit():
            raise ValidationError("Karta raqami faqat raqamlardan iborat bo'lishi kerak.")
        if len(card_number) != 16:
            raise ValidationError("Karta 16ta raqamdan iborat bo'lishi kerak.")
        return card_number

    def clean_amount(self):
        amount = self.cleaned_data['amount']

        if amount <= 0:
            raise ValidationError("Summa 0 dan katta bo'lishi kerak.")
        if self.user and amount > self.user.balance:
            raise ValidationError("Summa balansdan teng yoki kichik bo'lishi kerak.")
        return amount
