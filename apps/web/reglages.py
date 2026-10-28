"""Réglages de l'agence : équipe, clôture de période, lecture des règles en vigueur (gérant)."""

import calendar
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError as PasswordError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.services.public import AccountsService
from apps.ledger.services.public import LedgerService
from apps.shared_kernel.actor import Actor
from apps.shared_kernel.roles import Role
from apps.tenancy.services.public import TenancyService
from apps.web.access import _actor, agency_required
from apps.web.errors import attempt
from apps.web.forms import ClosePeriodForm, MemberForm

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip
HISTORY_MONTHS = 12


@dataclass(frozen=True)
class MonthRow:
    key: str
    label: str
    last_day: date
    closed: bool


def _manager(request: HttpRequest) -> Actor:
    actor = _actor(request)
    actor.require_manager()
    return actor


def _recent_months(closed_until: date | None) -> list[MonthRow]:
    """Les derniers mois terminés, du plus récent au plus ancien."""
    today = timezone.localdate()
    year, month = today.year, today.month
    rows: list[MonthRow] = []
    for _ in range(HISTORY_MONTHS):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        rows.append(
            MonthRow(
                key=f"{year:04d}-{month:02d}",
                label=f"{MONTHS_FR[month - 1]} {year}",
                last_day=last_day,
                closed=closed_until is not None and last_day <= closed_until,
            )
        )
    return rows


def _context(actor: Actor, *, member_form: MemberForm | None = None) -> dict[str, object]:
    closed_until = LedgerService.closed_until(actor)
    team = AccountsService.team(actor)
    months = _recent_months(closed_until)
    return {
        "agency": TenancyService.agency_info(actor),
        "team": team,
        "member_form": member_form or MemberForm(),
        "closed_until": closed_until,
        "months": months,
        "open_months": [row for row in months if not row.closed],
        "upcoming_days": settings.UPCOMING_DEPARTURE_DAYS,
        "session_hours": settings.SESSION_COOKIE_AGE // 3600,
        "lock_minutes": settings.LOGIN_LOCK_MINUTES,
        "max_failures": settings.LOGIN_MAX_FAILURES,
    }


@agency_required
@require_GET
def settings_page(request: HttpRequest) -> HttpResponse:
    actor = _manager(request)
    return render(request, "web/settings.html", _context(actor))


@agency_required
@require_POST
def member_add(request: HttpRequest) -> HttpResponse:
    actor = _manager(request)
    form = MemberForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        if AccountsService.find_user_id(data["username"]) is not None:
            form.add_error("username", "Cet identifiant est déjà pris.")
        else:
            try:
                attempt(
                    request,
                    lambda: AccountsService.create_member(
                        actor,
                        username=data["username"],
                        password=data["password"],
                        role=Role(data["role"]),
                    ),
                    f"{data['username']} peut maintenant se connecter.",
                )
            except PasswordError as error:
                form.add_error("password", error)
            else:
                return redirect("web:settings")
    return render(request, "web/settings.html", _context(actor, member_form=form), status=400)


@agency_required
@require_http_methods(["GET", "POST"])
def period_close(request: HttpRequest) -> HttpResponse:
    actor = _manager(request)
    key = request.POST.get("month") or request.GET.get("mois", "")
    row = next((month for month in _recent_months(None) if month.key == key), None)
    if row is None:
        messages.error(request, "Choisissez un des mois proposés.")
        return redirect("web:settings")
    if request.method == "POST":
        form = ClosePeriodForm(request.POST)
        if form.is_valid():
            attempt(
                request,
                lambda: LedgerService.close_period(actor, closed_until=row.last_day),
                f"La comptabilité est close jusqu'au {row.last_day.strftime('%d/%m/%Y')}.",
            )
            return redirect("web:settings")
    else:
        form = ClosePeriodForm(initial={"month": row.key})
    return render(
        request,
        "web/settings_close.html",
        {"form": form, "row": row},
        status=400 if form.is_bound else 200,
    )
