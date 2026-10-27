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
    path("dossiers/coller/", views.paste_booking, name="paste_booking"),
    path("dossiers/rapide/", views.quick_entry, name="quick_entry"),
    path("dossiers/", views.case_list, name="case_list"),
    path("dossiers/nouveau/", views.case_create, name="case_create"),
    path("dossiers/<uuid:case_id>/", views.case_detail, name="case_detail"),
    path("dossiers/<uuid:case_id>/lignes/", views.line_add, name="line_add"),
    path(
        "dossiers/<uuid:case_id>/lignes/<uuid:line_id>/emettre/",
        views.line_issue,
        name="line_issue",
    ),
    path(
        "dossiers/<uuid:case_id>/lignes/<uuid:line_id>/annuler/",
        views.line_void,
        name="line_void",
    ),
    path("dossiers/<uuid:case_id>/encaissements/", views.payment_add, name="payment_add"),
    path(
        "dossiers/<uuid:case_id>/encaissements/<uuid:payment_id>/annuler/",
        views.payment_void,
        name="payment_void",
    ),
    path("clients/", views.customer_list, name="customer_list"),
    path("dossiers/<uuid:case_id>/clore/", views.case_close, name="case_close"),
    path("dossiers/<uuid:case_id>/rouvrir/", views.case_reopen, name="case_reopen"),
]
