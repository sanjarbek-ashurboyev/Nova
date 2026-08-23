from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash, REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView
from django.contrib.auth.views import LogoutView as BaseLogoutView

from accounts.forms import LoginForm, RegisterForm, UserUpdateModelForm, UserPasswordUpdateForm
from accounts.models import Region, User


class LoginView(FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        phone = form.cleaned_data["phone"]
        password = form.cleaned_data["password"]

        user = authenticate(
            self.request,
            phone=phone,
            password=password,
        )

        if user is not None:
            login(self.request, user)
            return super().form_valid(form)

        form.add_error(
            None,
            "Telefon raqam yoki parol xato"
        )

        return self.form_invalid(form)

    def get_success_url(self):
        redirect_to = self.request.POST.get(REDIRECT_FIELD_NAME) or self.request.GET.get(REDIRECT_FIELD_NAME)
        if redirect_to and url_has_allowed_host_and_scheme(
                redirect_to,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
        ):
            return redirect_to

        if self.request.user.role == User.RoleChoices.OPERATOR:
            return reverse_lazy('operator:new-orders')
        if self.request.user.role == User.RoleChoices.DRIVER:
            return reverse_lazy('driver:available-orders')
        return reverse_lazy('catalog:home')


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        form = RegisterForm()
        ref = request.GET.get('ref') or request.GET.get('id')
        if ref:
            request.session['referrer_id'] = ref
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            referrer_id = request.session.get('referrer_id') or request.GET.get('ref')
            if referrer_id:
                try:
                    user.referrer = User.objects.get(pk=referrer_id)
                except (User.DoesNotExist, ValueError, TypeError):
                    pass

            user.save()
            login(request, user)
            messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli!")
            request.session.pop('referrer_id', None)
            return redirect('catalog:home')
        return render(request, self.template_name, {'form': form})


class LogoutView(BaseLogoutView):
    next_page = 'catalog:home'


class CabinetDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/cabinet.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['user'] = self.request.user
        data['active'] = 'dashboard'
        return data

class SettingsUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    queryset = User.objects.all()
    form_class = UserUpdateModelForm
    template_name = 'accounts/cabinet_settings.html'
    success_url = reverse_lazy('accounts:cabinet-settings')
    context_object_name = 'user'
    success_message = "Ma'lumotlaringiz saqlandi"

    def get_context_data(self, **kwargs):
        data =  super().get_context_data(**kwargs)
        data['regions'] = Region.objects.prefetch_related('districts').all()
        data['active'] = 'settings'
        return data

    def get_object(self, queryset=None):
        return self.request.user

class SettingsPasswordUpdateView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'accounts/cabinet_settings.html'
    form_class = UserPasswordUpdateForm
    success_url = reverse_lazy('accounts:cabinet-settings')
    success_message = "Parol o'zgartirildi"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['user'] = self.request.user
        data['regions'] = Region.objects.prefetch_related('districts').all()
        data['active'] = 'settings'
        return data

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        return super().form_valid(form)


class ReferralListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/cabinet_referral.html'
    context_object_name = 'referrals'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(referrer=self.request.user).order_by('-date_joined')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['referral_count'] = self.get_queryset().count()
        data['active'] = 'referral'
        return data
