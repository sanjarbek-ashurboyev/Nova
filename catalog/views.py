from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView
from django.views.generic.edit import FormMixin

from catalog.forms import ThreadModelForm
from catalog.models import Category, Product, Thread
from orders.forms import OrderCreateForm
from orders.models import Order


class HomeView(View):
    def get(self, request):
        categories = Category.objects.all()
        products = Product.objects.filter(is_bestseller=True).prefetch_related('images')
        new_products = Product.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).prefetch_related('images')

        return render(request,"catalog/home.html", {
            "categories": categories,
            'products': products,
            'new_products': new_products
        })

class CategoryDetailView(DetailView):
    model = Category
    context_object_name = 'category'
    template_name = 'catalog/product_list.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['products'] = self.object.products.prefetch_related('images')
        data['categories'] = Category.objects.all()
        return data

class ProductListView(ListView):
    queryset = Product.objects.prefetch_related('images')
    context_object_name = 'products'
    template_name = 'catalog/product_list.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['categories'] = Category.objects.all()
        return data

class ProductSearchListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Product.objects.none()

        return Product.objects.filter(name__icontains=query).prefetch_related('images')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['categories'] = Category.objects.all()
        data['query'] = self.request.GET.get('q', '')
        return data



class ProductDetailView(FormMixin, DetailView):
    queryset =  Product.objects.prefetch_related('images')
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    form_class = OrderCreateForm
    thread = None
    MAX_QUANTITY = 9

    def get_success_url(self):
        return reverse('catalog:product-detail', kwargs={'slug': self.object.slug})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product'] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['categories'] = Category.objects.all()
        data['category'] = self.object.category
        data['thread'] = self.thread
        data['price'] = self.object.price - (self.thread.discount if self.thread else 0)
        stock = max(self.object.stock, 0)
        data['in_stock'] = stock > 0
        data['quantity_choices'] = range(1, min(stock, self.MAX_QUANTITY) + 1)
        order_id = self.request.session.pop('accepted_order_id', None)
        if order_id:
            data['accepted_order'] = Order.objects.filter(pk=order_id).first()
        return data

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        quantity = form.cleaned_data['quantity']

        claimed = (Product.objects
                   .filter(pk=self.object.pk, stock__gte=quantity)
                   .update(stock=F('stock') - quantity))
        if not claimed:
            self.object.refresh_from_db(fields=['stock'])
            form.add_error('quantity', "Kechirasiz, omborda yetarli mahsulot qolmadi.")
            return self.form_invalid(form)

        order = form.save(commit=False)
        order.product = self.object
        order.thread = self.thread
        order.user = self.request.user if self.request.user.is_authenticated else None
        order.customer_name = form.cleaned_data['fullname']
        order.phone = form.cleaned_data['phone_number']
        order.save()
        self.request.session['accepted_order_id'] = order.pk
        return super().form_valid(form)


class ThreadDetailView(ProductDetailView):
    def get_object(self, queryset=None):
        self.thread = get_object_or_404(
            Thread.objects.select_related('product'), pk=self.kwargs['pk']
        )
        return self.thread.product

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.user.pk != self.thread.user_id:
            Thread.objects.filter(pk=self.thread.pk).update(visit_count=F('visit_count') + 1)
        return response

    def get_success_url(self):
        return reverse('catalog:thread-detail', kwargs={'pk': self.thread.pk})


class ThreadMarketListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'accounts/cabinet_market.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.prefetch_related('images')
        slug = self.kwargs.get('slug')
        q = self.request.GET.get('q')
        if slug:
            qs = qs.filter(category__slug=slug)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data['categories'] = Category.objects.all()
        data['active'] = 'market'
        data['query'] = self.request.GET.get('q', '')
        data['current'] = self.kwargs.get('slug')
        return data


class ThreadCreateView(LoginRequiredMixin, CreateView):
    form_class = ThreadModelForm
    success_url = reverse_lazy('catalog:cabinet-threads')
    http_method_names = ['post']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect('catalog:cabinet-market')

class ThreadListView(LoginRequiredMixin, ListView):
    template_name = 'accounts/cabinet_threads.html'
    context_object_name = 'threads'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['active'] = 'links'
        data['query'] = self.request.GET.get('q', '')
        return data

    def get_queryset(self):
        qs = Thread.objects.filter(user=self.request.user).order_by('-id')
        query = self.request.GET.get('q', '').strip()

        if query:
            condition = Q(name__icontains=query)
            qs = qs.filter(condition)

        return qs

class ThreadDeleteView(LoginRequiredMixin, DeleteView):
    model = Thread
    success_url = reverse_lazy('catalog:cabinet-threads')
    http_method_names = ['post']

    def get_queryset(self):
        return Thread.objects.filter(user=self.request.user)
