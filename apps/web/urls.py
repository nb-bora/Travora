from django.contrib.auth import views as auth_views
from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("", views.today, name="today"),
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="web/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
]
