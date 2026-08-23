from django import forms
from django.contrib import admin

from orders.models import Payment


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        amount = cleaned.get('amount')
        user = cleaned.get('user')

        if status != Payment.Status.PAID:
            return cleaned

        if not cleaned.get('receipt') and not self.instance.receipt:
            self.add_error('receipt', "To'langan deb belgilash uchun chek yuklang.")

        if amount is None or user is None:
            return cleaned

        already_paid = self.instance.pk and getattr(self.instance, '_loaded_status', None) == Payment.Status.PAID
        charge = amount - self.instance._loaded_amount if already_paid else amount

        if charge > user.balance:
            raise forms.ValidationError(
                f"Foydalanuvchi balansi yetarli emas: balans {user.balance}, yechilishi kerak {charge}."
            )
        return cleaned


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentAdminForm
    list_display = ['id', 'user', 'amount', 'status', 'user_balance', 'has_receipt', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__phone', 'user__first_name', 'user__last_name', 'card_number']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    @admin.display(description='Balans', ordering='user__balance')
    def user_balance(self, obj):
        return obj.user.balance

    @admin.display(description='Chek', boolean=True)
    def has_receipt(self, obj):
        return bool(obj.receipt)
