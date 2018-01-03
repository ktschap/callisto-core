import logging

from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import is_safe_url
from django.views.generic.edit import CreateView

from callisto_core.utils.api import TenantApi

from .forms import FormattedPasswordResetForm, LoginForm, SignUpForm
from .models import Account

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomSignupView(CreateView):
    template_name = 'callisto_core/accounts/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if TenantApi.site_settings(
            'DISABLE_SIGNUP',
            cast=bool,
                request=request):
            return redirect(reverse('login'))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        next_page = self.request.GET.get('next', None)
        if next_page and is_safe_url(next_page, self.request.get_host()):
            return next_page
        else:
            return super().get_success_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        Account.objects.create(
            user=form.instance,
            site_id=self.request.site.id,
        )
        login(self.request, form.instance)
        return response


class CustomLoginView(LoginView):
    template_name = 'callisto_core/accounts/login.html'
    authentication_form = LoginForm

    def get_template_names(self):
        if TenantApi.site_settings(
            'DISABLE_SIGNUP',
            cast=bool,
            request=self.request,
        ):
            self.template_name = 'callisto_core/accounts/login_signup_disabled.html'
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        current_site = self.request.site
        context.update({
            self.redirect_field_name: self.get_redirect_url(),
            'site': current_site,
            'site_name': current_site.name,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class CustomPasswordResetView(PasswordResetView):
    template_name = 'callisto_core/accounts/password_reset.html'
    email_template_name = 'callisto_core/accounts/password_reset_email.html'
    success_url = reverse_lazy('password_reset_sent')
    form_class = FormattedPasswordResetForm


class CustomLogoutView(LogoutView):

    def get_context_data(self, **kwargs):
        context = super(LogoutView, self).get_context_data(**kwargs)
        current_site = self.request.site
        context.update({
            'site': current_site,
            'site_name': current_site.name,
            'title': 'Logged out',
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context
