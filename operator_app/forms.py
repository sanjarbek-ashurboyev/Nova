from django.core.exceptions import ValidationError
from django.forms import CharField
from django.forms.models import ModelForm

from orders.models import Order

REQUIRED = {'required': "Bu maydon to'ldirilishi shart."}
INVALID_CHOICE = {'invalid_choice': "Tanlangan qiymat noto'g'ri."}


class ChangeOrderForm(ModelForm):
    comment = CharField(max_length=500, required=False, label='Izoh')

    class Meta:
        model = Order
        fields = ['status']
        labels = {'status': 'Holati'}
        error_messages = {'status': REQUIRED | INVALID_CHOICE}


class OrderDetailForm(ModelForm):
    comment = CharField(max_length=500, required=False, label='Izoh')

    class Meta:
        model = Order
        fields = ['customer_name', 'phone', 'quantity', 'district', 'address', 'status']
        labels = {
            'customer_name': 'Mijoz ismi',
            'phone': 'Telefon',
            'quantity': 'Miqdori',
            'district': 'Tuman',
            'address': 'Manzil',
            'status': 'Holati',
        }
        error_messages = {
            'customer_name': REQUIRED,
            'phone': REQUIRED,
            'quantity': REQUIRED | {'invalid': "Miqdor butun son bo'lishi kerak.",
                                    'min_value': "Miqdor 1 dan kam bo'lmasin."},
            'district': INVALID_CHOICE,
            'address': REQUIRED,
            'status': REQUIRED | INVALID_CHOICE,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].required = True

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        delta = quantity - (self.instance.quantity or 0)
        if delta > 0 and delta > self.instance.product.stock:
            raise ValidationError(
                f"Omborda faqat {max(self.instance.product.stock, 0)} dona qo'shimcha qoldi."
            )
        return quantity

