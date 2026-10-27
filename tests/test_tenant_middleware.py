from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.shared_kernel.roles import Role
from apps.shared_kernel.tenant_context import (
    AGENCY_SETTING,
    _get_setting,
    current_agency_id,
)
from apps.tenancy.middleware import TenantMiddleware
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture


def build_request(user: object) -> HttpRequest:
    request = RequestFactory().get("/")
    request.user = user  # type: ignore[assignment]
    return request


def test_an_authenticated_request_runs_inside_its_agency_scope(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    seen: dict[str, object] = {}

    def view(request: HttpRequest) -> HttpResponse:
        seen["agency"] = current_agency_id()
        seen["setting"] = _get_setting(AGENCY_SETTING)
        seen["actor"] = request.actor  # type: ignore[attr-defined]
        return HttpResponse("ok")

    request = build_request(User.objects.get(id=agency_a.agent.user_id))
    response = TenantMiddleware(view)(request)

    assert response.status_code == 200
    assert seen["agency"] == agency_a.id
    assert seen["setting"] == str(agency_a.id)
    assert seen["actor"] == agency_a.agent
    assert seen["actor"].role is Role.AGENT  # type: ignore[attr-defined]
    assert current_agency_id() is None
    assert _get_setting(AGENCY_SETTING) == ""


def test_the_agency_is_never_taken_from_the_request(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    def view(request: HttpRequest) -> HttpResponse:
        assert current_agency_id() == agency_a.id
        return HttpResponse("ok")

    request = RequestFactory().get(
        "/", {"agency": str(agency_b.id)}, HTTP_X_AGENCY=str(agency_b.id)
    )
    request.user = User.objects.get(id=agency_a.manager.user_id)
    assert TenantMiddleware(view)(request).status_code == 200


def test_anonymous_and_unattached_users_get_no_agency(agency_a: AgencyFixture) -> None:
    def view(request: HttpRequest) -> HttpResponse:
        assert current_agency_id() is None
        return HttpResponse("ok")

    anonymous = build_request(AnonymousUser())
    TenantMiddleware(view)(anonymous)
    assert anonymous.actor is None  # type: ignore[attr-defined]

    ghost = User.objects.create_user(username="ghost", password="x")
    unattached = build_request(ghost)
    TenantMiddleware(view)(unattached)
    assert unattached.actor is None  # type: ignore[attr-defined]


def test_a_server_error_rolls_back_the_requests_writes(agency_a: AgencyFixture) -> None:
    def view(request: HttpRequest) -> HttpResponse:
        AuditEvent.objects.create(action="boom", object_type="x", object_id=agency_a.id)
        return HttpResponse("erreur", status=500)

    request = build_request(User.objects.get(id=agency_a.manager.user_id))
    assert TenantMiddleware(view)(request).status_code == 500

    with TenancyService.scope(agency_a.id):
        assert not AuditEvent.objects.filter(action="boom").exists()


def test_a_successful_request_keeps_its_writes(agency_a: AgencyFixture) -> None:
    def view(request: HttpRequest) -> HttpResponse:
        AuditEvent.objects.create(action="kept", object_type="x", object_id=agency_a.id)
        return HttpResponse("ok")

    request = build_request(User.objects.get(id=agency_a.manager.user_id))
    TenantMiddleware(view)(request)

    with TenancyService.scope(agency_a.id):
        assert AuditEvent.objects.filter(action="kept").exists()
