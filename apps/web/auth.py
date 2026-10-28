"""Connexion : formulaire qui ralentit les devinettes, et page sans surprise pour un connecté."""

from typing import Any

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect

from apps.accounts.services.public import AccountsService


class ThrottledAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Identifiant ou mot de passe incorrect.",
    }

    def clean(self) -> dict[str, Any]:
        username = self.data.get("username", "")
        if username and AccountsService.too_many_login_failures(username=username):
            raise forms.ValidationError(
                f"Trop de tentatives. Réessayez dans {settings.LOGIN_LOCK_MINUTES} minutes.",
                code="throttled",
            )
        try:
            return super().clean()
        except forms.ValidationError:
            request = self.request
            address = request.META.get("REMOTE_ADDR") if request is not None else None
            AccountsService.record_login_failure(username=username, ip_address=address)
            raise


class WebLoginView(LoginView):
    template_name = "web/login.html"
    authentication_form = ThrottledAuthenticationForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        # Un utilisateur déjà connecté repart toujours de l'accueil, quel que soit « next ».
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["lock_minutes"] = settings.LOGIN_LOCK_MINUTES
        return context

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        AccountsService.clear_login_failures(username=form.cleaned_data["username"])
        return super().form_valid(form)
