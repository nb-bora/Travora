from django.contrib.auth import views as auth_views
from django.urls import path

from apps.web import insights, views
from apps.web.auth import WebLoginView
from apps.web.flows import views as flows

app_name = "web"

urlpatterns = [
    path("", views.today, name="today"),
    path("connexion/", WebLoginView.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("dossiers/coller/", views.paste_booking, name="paste_booking"),
    path("nouveau/", flows.flow_chooser, name="flow_chooser"),
    path("nouveau/<slug:mode>/", flows.flow_start, name="flow_start"),
    path("nouveau/<slug:mode>/etape/<int:step>/", flows.flow_step, name="flow_step"),
    path("dossiers/<uuid:case_id>/paiement/", flows.flow_pay, name="flow_pay"),
    path("dossiers/<uuid:case_id>/remise/", flows.flow_done, name="flow_done"),
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
    path("clients/<uuid:customer_id>/", insights.customer_detail, name="customer_detail"),
    path("clients/<uuid:customer_id>/export/", insights.customer_export, name="customer_export"),
    path("rapports/", insights.report, name="report"),
    path("rapports/export/", insights.report_export, name="report_export"),
    path("dossiers/<uuid:case_id>/clore/", views.case_close, name="case_close"),
    path("dossiers/<uuid:case_id>/rouvrir/", views.case_reopen, name="case_reopen"),
]
