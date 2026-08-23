from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView, DetailView
from django.views.generic.edit import FormMixin

from accounts.models import User, Region
from catalog.models import Product
from operator_app.forms import ChangeOrderForm, OrderDetailForm
from orders.models import Order, Survey


class OperatorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == User.RoleChoices.OPERATOR


class OperatorCountsMixin:
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['new_orders_count'] = Order.objects.filter(
            status=Order.OrderStatus.NEW, operator__isnull=True,
        ).count()
        data['my_orders_count'] = Order.objects.filter(operator=self.request.user).count()
        return data


class NewOrdersListView(OperatorRequiredMixin, OperatorCountsMixin, ListView):
    model = Order
    template_name = 'operator/new_orders.html'
    context_object_name = 'orders'
    paginate_by = 15

    def get_queryset(self):
        qs = (Order.objects
              .filter(status=Order.OrderStatus.NEW, operator__isnull=True)
              .select_related('product__category', 'thread')
              .order_by('-created_at'))

        query = (self.request.GET.get('q') or '').strip()
        if query:
            condition = Q(customer_name__icontains=query) | Q(phone__icontains=query)
            digits = query.lstrip('#')
            if digits.isdigit():
                condition |= Q(id=int(digits))
            qs = qs.filter(condition)
        return qs


class OperatorTakeOrderView(OperatorRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request):
        order_id = (request.POST.get('id') or '').strip()
        if not order_id.isdigit():
            messages.warning(request, "Buyurtma raqami noto'g'ri.")
            return redirect('operator:new-orders')

        claimed = (Order.objects
                   .filter(id=int(order_id),
                           status=Order.OrderStatus.NEW,
                           operator__isnull=True)
                   .update(operator=request.user))

        if claimed:
            messages.success(request, f"Buyurtma #{order_id} sizga biriktirildi.")
        else:
            messages.warning(request, "Bu buyurtma allaqachon olingan yoki mavjud emas.")
        return redirect('operator:new-orders')


class OperatorOrdersListView(OperatorRequiredMixin, OperatorCountsMixin, ListView):
    model = Order
    template_name = 'operator/orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return (Order.objects
                .filter(operator=self.request.user)
                .select_related('product__category', 'thread', 'district__region')
                .order_by('-created_at'))


class OperatorTakeNextOrderView(OperatorRequiredMixin, View):
    http_method_names = ['post']
    MAX_ATTEMPTS = 5

    def post(self, request):
        for _ in range(self.MAX_ATTEMPTS):
            order = (Order.objects
                     .filter(status=Order.OrderStatus.NEW, operator__isnull=True)
                     .order_by('created_at')
                     .first())
            if order is None:
                messages.info(request, "Navbatda buyurtma qolmadi.")
                return redirect('operator:new-orders')

            claimed = (Order.objects
                       .filter(pk=order.pk,
                               status=Order.OrderStatus.NEW,
                               operator__isnull=True)
                       .update(operator=request.user))
            if claimed:
                messages.success(request, f"Buyurtma #{order.pk} sizga biriktirildi.")
                return redirect('operator:new-orders')

        messages.warning(request, "Navbat band, qayta urinib ko'ring.")
        return redirect('operator:new-orders')


class OperatorOrderUpdateView(OperatorRequiredMixin, UpdateView):
    model = Order
    form_class = ChangeOrderForm
    template_name = 'operator/orders.html'
    http_method_names = ['post']
    success_url = reverse_lazy('operator:my-orders')

    def get_queryset(self):
        return Order.objects.filter(operator=self.request.user)

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        Survey.objects.update_or_create(
            order=self.object,
            defaults={
                'operator': self.request.user,
                'comment': form.cleaned_data['comment'],
            },
        )
        return response


class OperatorOrderDetailView(OperatorRequiredMixin, OperatorCountsMixin, FormMixin, DetailView):
    model = Order
    form_class = OrderDetailForm
    template_name = 'operator/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(operator=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def get_success_url(self):
        return reverse('operator:my-orders')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        delta = form.cleaned_data['quantity'] - (form.initial.get('quantity') or 0)
        if delta > 0:
            claimed = (Product.objects
                       .filter(pk=self.object.product_id, stock__gte=delta)
                       .update(stock=F('stock') - delta))
            if not claimed:
                form.add_error('quantity', "Omborda yetarli mahsulot qolmadi.")
                return self.form_invalid(form)
        elif delta < 0:
            Product.objects.filter(pk=self.object.product_id).update(stock=F('stock') - delta)

        self.object = form.save()
        Survey.objects.update_or_create(
            order=self.object,
            defaults={
                'operator': self.request.user,
                'comment': form.cleaned_data['comment'],
            },
        )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        data['districts_json'] = {
            str(region.id): [[d.id, d.title] for d in region.districts.all()]
            for region in Region.objects.prefetch_related('districts')
        }
        data['current_customer_orders'] = (
            Order.objects
            .filter(phone=self.object.phone)
            .exclude(pk=self.object.pk)
            .select_related('product', 'thread')
            .order_by('-created_at')
        )
        return data
