from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView

from accounts.models import User
from catalog.models import Thread
from orders.forms import PaymentForm
from orders.models import Order, Payment


class PaymentRequestView(LoginRequiredMixin, FormView):
    form_class = PaymentForm
    template_name = 'accounts/cabinet_payment.html'
    success_url = reverse_lazy('orders:cabinet-payments')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        payments = Payment.objects.filter(user=self.request.user)
        data['payments'] = payments
        data['pending_payment'] = payments.filter(status=Payment.Status.NEW).first()
        data['active'] = 'payment'
        return data

    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.user = self.request.user
        try:
            payment.save()
        except IntegrityError:
            form.add_error(None, "Sizda ko'rib chiqilmagan to'lov so'rovi mavjud.")
            return self.form_invalid(form)
        messages.success(self.request, "So'rov qabul qilindi.")
        return super().form_valid(form)


class PaymentReceiptDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, user=request.user)

        if not payment.receipt:
            raise Http404("Chek mavjud emas")

        try:
            handle = payment.receipt.open('rb')
        except FileNotFoundError:
            raise Http404("Chek fayli topilmadi") from None

        extension = Path(payment.receipt.name).suffix
        filename = f"chek-{payment.pk}-{payment.created_at:%Y%m%d}{extension}"
        return FileResponse(handle, as_attachment=True, filename=filename)


class ThreadStatsListView(LoginRequiredMixin, ListView):
    model = Thread
    template_name = 'accounts/cabinet_stats.html'
    context_object_name = 'threads'
    paginate_by = 20
    ordering = '-id'

    DECIMAL = DecimalField(max_digits=12, decimal_places=0)

    total_fields = ['visit_count', 'delivered_qty', 'delivered_sum'] + [
        f'{value}_count' for value, _ in Order.OrderStatus.choices
    ]

    def get_queryset(self):
        status_counts = {
            f'{value}_count': Count('orders', filter=Q(orders__status=value))
            for value, _ in Order.OrderStatus.choices
        }

        return (
            super().get_queryset()
            .filter(user=self.request.user)
            .select_related('product')
            .annotate(
                delivered_qty=Coalesce(
                    Sum('orders__quantity', filter=Q(orders__status=Order.OrderStatus.DELIVERED)), 0
                ),
                **status_counts,
            )
            .annotate(unit_profit=F('product__return_price') - F('discount'))
            .annotate(
                delivered_sum=ExpressionWrapper(
                    F('unit_profit') * F('delivered_qty'),
                    output_field=self.DECIMAL,
                )
            )
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['active'] = 'stats'
        data['totals'] = self.get_totals()
        return data

    def get_totals(self):
        user = self.request.user
        delivered = Q(status=Order.OrderStatus.DELIVERED)
        unit_profit = F('thread__product__return_price') - F('thread__discount')

        totals = Order.objects.filter(thread__user=user).aggregate(
            delivered_qty=Coalesce(Sum('quantity', filter=delivered), 0),
            delivered_sum=Coalesce(
                Sum(ExpressionWrapper(unit_profit * F('quantity'),
                                      output_field=self.DECIMAL), filter=delivered),
                Value(0), output_field=self.DECIMAL,
            ),
            **{f'{value}_count': Count('pk', filter=Q(status=value))
               for value, _ in Order.OrderStatus.choices},
        )
        totals['visit_count'] = Thread.objects.filter(user=user).aggregate(
            total=Coalesce(Sum('visit_count'), 0),
        )['total']
        return totals


class SellerContestListView(LoginRequiredMixin, ListView):
    model = User
    context_object_name = 'sellers'
    template_name = 'accounts/cabinet_contest.html'
    paginate_by = 20

    def get_queryset(self):
        return (
            super().get_queryset()
            .annotate(
                sold=Coalesce(
                    Sum(
                        'threads__orders__quantity',
                        filter=Q(threads__orders__status=Order.OrderStatus.DELIVERED),
                    ),
                    0,
                )
            )
            .filter(sold__gt=0)
            .order_by('-sold', 'id')
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['active'] = 'competition'
        return data


class OrderSurveyListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'accounts/cabinet_survey.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(thread__user=self.request.user)
            .select_related('thread', 'survey', 'survey__operator', 'user__district__region')
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['active'] = 'requests'
        return data
