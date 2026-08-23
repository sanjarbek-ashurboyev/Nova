from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from accounts.models import Region, User
from orders.models import Order


class DriverRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == User.RoleChoices.DRIVER


class DriverCountsMixin:
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['available_count'] = Order.objects.filter(
            status=Order.OrderStatus.SHIPPING, driver__isnull=True,
        ).count()
        data['my_count'] = Order.objects.filter(
            driver=self.request.user, status=Order.OrderStatus.SHIPPING,
        ).count()
        return data


class AvailableOrdersListView(DriverRequiredMixin, DriverCountsMixin, ListView):
    model = Order
    template_name = 'driver/available_orders.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = (Order.objects
              .filter(status=Order.OrderStatus.SHIPPING, driver__isnull=True)
              .select_related('product', 'district__region')
              .order_by('-created_at', '-id'))

        region = (self.request.GET.get('region') or '').strip()
        if region.isdigit():
            qs = qs.filter(district__region_id=int(region))

        query = (self.request.GET.get('q') or '').strip()
        if query:
            condition = (Q(customer_name__icontains=query)
                         | Q(phone__icontains=query)
                         | Q(address__icontains=query)
                         | Q(district__title__icontains=query))
            digits = query.lstrip('#')
            if digits.isdigit():
                condition |= Q(id=int(digits))
            qs = qs.filter(condition)
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.order_by('title')
        data['selected_region'] = (self.request.GET.get('region') or '').strip()
        data['active'] = 'available'
        return data


class DriverTakeOrderView(DriverRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        claimed = (Order.objects
                   .filter(pk=pk,
                           status=Order.OrderStatus.SHIPPING,
                           driver__isnull=True)
                   .update(driver=request.user, taken_at=timezone.now()))

        if claimed:
            messages.success(request, f"Buyurtma #{pk} sizga biriktirildi.")
        else:
            messages.warning(request, "Bu buyurtma allaqachon olingan yoki mavjud emas.")
        return redirect('driver:available-orders')


class DriverOrdersListView(DriverRequiredMixin, DriverCountsMixin, ListView):
    model = Order
    template_name = 'driver/my_orders.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = (Order.objects
              .filter(driver=self.request.user)
              .select_related('product__category', 'district__region', 'operator')
              .order_by('-taken_at', '-id'))

        status = self.request.GET.get('status')
        if status == 'delivered':
            qs = qs.filter(status=Order.OrderStatus.DELIVERED)
        elif status != 'all':
            qs = qs.filter(status=Order.OrderStatus.SHIPPING)
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['selected_status'] = self.request.GET.get('status') or 'active'
        data['delivered_count'] = Order.objects.filter(
            driver=self.request.user, status=Order.OrderStatus.DELIVERED,
        ).count()
        data['active'] = 'my_orders'
        return data


class DriverDeliverOrderView(DriverRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        delivered = (Order.objects
                     .filter(pk=pk,
                             driver=request.user,
                             status=Order.OrderStatus.SHIPPING)
                     .update(status=Order.OrderStatus.DELIVERED,
                             delivered_at=timezone.now()))

        if delivered:
            messages.success(request, f"Buyurtma #{pk} yetkazildi deb belgilandi.")
        else:
            messages.warning(request, "Buyurtma topilmadi yoki allaqachon yakunlangan.")
        return redirect('driver:my-orders')
