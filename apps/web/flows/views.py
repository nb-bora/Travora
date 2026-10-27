"""Vues des parcours guidés (avion, bus, train, bateau)."""

import uuid
from datetime import date
from typing import Any
from uuid import UUID

from django import forms
from django.db import IntegrityError
from django.forms import BaseFormSet, formset_factory
from django.http import Http404, HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.cases.dto import CaseDetail
from apps.cases.exceptions import CaseNotFound, InvalidLine
from apps.cases.services.public import CasesService
from apps.crm.services.public import CrmService
from apps.payments.constants import PaymentMethod
from apps.payments.services.public import PaymentsService
from apps.shared_kernel.actor import Actor
from apps.tenancy.services.public import TenancyService
from apps.web.access import _actor, agency_required
from apps.web.errors import attempt
from apps.web.flows.base import FlowDef
from apps.web.flows.fields import WebForm, date_field
from apps.web.flows.registry import FLOWS
from apps.web.flows.spec import (
    MAX_TRAVELLERS,
    MODE_BY_KIND,
    MODES,
    clear_draft,
    get_draft,
    new_draft,
    save_draft,
    to_json,
)

DONE_FLOWS = "flow_done"
STEP_COUNT = 5


def _flow(mode: str) -> FlowDef:
    flow = FLOWS.get(mode)
    if flow is None:
        raise Http404
    return flow


def _stepper(flow: FlowDef, current: int) -> list[dict[str, Any]]:
    steps = []
    for index, label in enumerate(flow.mode.steps, start=1):
        state = "done" if index < current else "current" if index == current else "todo"
        steps.append({"n": index, "label": label, "state": state, "last": index == STEP_COUNT})
    return steps


def _layout(
    flow: FlowDef,
    current: int,
    *,
    title: str,
    subtitle: str,
    back_url: str,
    cta: str,
    footer_label: str = "",
    footer_total: int | None = None,
    **extra: object,
) -> dict[str, object]:
    return {
        "flow": flow.mode,
        "steps": _stepper(flow, current),
        "step": current,
        "title": title,
        "subtitle": subtitle,
        "back_url": back_url,
        "cta": cta,
        "footer_label": footer_label,
        "footer_total": footer_total,
        "close_url": reverse("web:flow_chooser"),
        **extra,
    }


# --- brouillon ----------------------------------------------------------------------------


def _draft_or_none(request: HttpRequest, flow: FlowDef) -> dict[str, Any] | None:
    return get_draft(request, flow.mode.slug)


def _step_url(flow: FlowDef, step: int) -> str:
    return reverse("web:flow_step", kwargs={"mode": flow.mode.slug, "step": step})


class UniqueFormSet(BaseFormSet):
    """Refuse deux voyageurs avec le même numéro de billet, la même place…"""

    def clean(self) -> None:
        super().clean()
        for field in getattr(self.form, "UNIQUE", ()):
            seen: set[str] = set()
            for form in self.forms:
                if not getattr(form, "cleaned_data", None) or form.cleaned_data.get("DELETE"):
                    continue
                value = str(form.cleaned_data.get(field, "")).strip().upper()
                if value and value in seen:
                    raise forms.ValidationError(
                        f"« {value} » est saisi deux fois : chaque voyageur a le sien."
                    )
                seen.add(value)


def _formset_class(flow: FlowDef) -> type[BaseFormSet]:
    return formset_factory(
        flow.traveller_form,
        formset=UniqueFormSet,
        extra=0,
        can_delete=True,
        max_num=MAX_TRAVELLERS,
        validate_max=True,
    )


def _raw_rows(post: QueryDict, prefix: str, fields: list[str]) -> list[dict[str, str]]:
    """Lignes telles que saisies, sans validation (ajout ou retrait d'une ligne)."""
    try:
        total = min(int(post.get(f"{prefix}-TOTAL_FORMS", "0") or 0), MAX_TRAVELLERS)
    except ValueError:
        total = 0
    rows = []
    for index in range(total):
        if post.get(f"{prefix}-{index}-DELETE"):
            continue
        rows.append({field: post.get(f"{prefix}-{index}-{field}", "") for field in fields})
    return rows


def _filled(forms_: list[forms.Form]) -> list[dict[str, Any]]:
    return [
        dict(form.cleaned_data)
        for form in forms_
        if getattr(form, "cleaned_data", None) and not form.cleaned_data.get("DELETE")
    ]


# --- chooser et démarrage -----------------------------------------------------------------


@agency_required
@require_GET
def flow_chooser(request: HttpRequest) -> HttpResponse:
    _actor(request)
    cards = [
        {"mode": mode, "draft": get_draft(request, slug) is not None}
        for slug, mode in MODES.items()
        if slug in FLOWS
    ]
    return render(request, "web/flow/chooser.html", {"cards": cards})


@agency_required
@require_GET
def flow_start(request: HttpRequest, mode: str) -> HttpResponse:
    flow = _flow(mode)
    _actor(request)
    if not request.GET.get("reprendre") or get_draft(request, mode) is None:
        save_draft(request, new_draft(mode, uuid.uuid4().hex))
    return redirect(_step_url(flow, 1))


# --- étapes 1 à 3 -------------------------------------------------------------------------


@agency_required
@require_http_methods(["GET", "POST"])
def flow_step(request: HttpRequest, mode: str, step: int) -> HttpResponse:
    flow = _flow(mode)
    actor = _actor(request)
    draft = _draft_or_none(request, flow)
    if draft is None:
        return redirect("web:flow_start", mode=mode)
    if step == 1:
        return _step_trip(request, actor, flow, draft)
    if step == 2:
        if not draft["trip"]:
            return redirect(_step_url(flow, 1))
        return _step_travellers(request, actor, flow, draft)
    if step == 3:
        if not draft["trip"]:
            return redirect(_step_url(flow, 1))
        if not draft["travellers"] or (flow.pricing_step == 2 and not draft["pricing"]):
            return redirect(_step_url(flow, 2))
        return _step_confirm(request, actor, flow, draft)
    raise Http404


def _title(flow: FlowDef) -> str:
    return f"Nouveau dossier · {flow.mode.label}"


def _step_trip(
    request: HttpRequest, actor: Actor, flow: FlowDef, draft: dict[str, Any]
) -> HttpResponse:
    extra: dict[str, object] = {}
    form: forms.Form
    if request.method == "POST":
        action = request.POST.get("action", "next")
        if action == "paste" and hasattr(flow, "paste"):
            proposal = flow.paste(request.POST.get("text", ""))
            draft.update(proposal.draft)
            save_draft(request, draft)
            form = flow.trip_form(initial=draft["trip"])
            extra.update(
                {
                    "proposal": proposal.proposal,
                    "pasted_text": request.POST.get("text", ""),
                    "timeline": proposal.timeline,
                    "recognised_count": proposal.count,
                }
            )
        else:
            form = flow.trip_form(request.POST)
            if form.is_valid():
                draft["trip"] = to_json(form.cleaned_data)
                save_draft(request, draft)
                return redirect(_step_url(flow, 2))
    else:
        form = flow.trip_form(initial=draft["trip"])
        if request.GET.get("saisie") != "manuelle" and hasattr(flow, "paste"):
            extra["paste_first"] = True
    context = _layout(
        flow,
        1,
        title=_title(flow),
        subtitle="Brouillon enregistré · rien n'est écrit avant la confirmation de la vente",
        back_url=reverse("web:flow_chooser"),
        cta="Continuer",
        footer_label=flow.step1_hint(draft),
        footer_total=flow.step1_total(draft),
        form=form,
        draft=draft,
        manual=request.GET.get("saisie") == "manuelle",
        **extra,
    )
    status = 422 if request.method == "POST" and form.errors else 200
    return render(request, f"{flow.template_prefix}_1.html", context, status=status)


def _traveller_context(
    flow: FlowDef,
    draft: dict[str, Any],
    formset: BaseFormSet,
    extra_forms: dict[str, forms.Form],
    **more: object,
) -> dict[str, object]:
    return _layout(
        flow,
        2,
        title=_title(flow),
        subtitle=flow.subtitle(draft),
        back_url=_step_url(flow, 1),
        cta="Continuer",
        footer_label=flow.step2_hint(draft),
        footer_total=flow.step2_total(draft),
        formset=formset,
        draft=draft,
        **extra_forms,
        **more,
    )


def _step_travellers(
    request: HttpRequest, actor: Actor, flow: FlowDef, draft: dict[str, Any]
) -> HttpResponse:
    formset_class = _formset_class(flow)
    fields = list(flow.traveller_form.base_fields)
    side: dict[str, forms.Form] = {}
    if request.method == "POST":
        action = request.POST.get("action", "next")
        if action in ("add", "remove"):
            rows = _raw_rows(request.POST, "form", fields)
            if action == "add" and len(rows) < MAX_TRAVELLERS:
                rows.append({})
            formset = formset_class(initial=rows or [{}])
            side = flow.side_forms(request.POST, draft, bound=False)
            return render(
                request,
                f"{flow.template_prefix}_2.html",
                _traveller_context(flow, draft, formset, side),
            )
        formset = formset_class(request.POST, initial=draft["travellers"])
        side = flow.side_forms(request.POST, draft, bound=True)
        valid = formset.is_valid() and all(f.is_valid() for f in side.values())
        rows = _filled(list(formset.forms)) if valid else []
        missing = ""
        if valid and not rows:
            valid = False
            missing = f"Ajoutez au moins un {flow.mode.traveller_word}."
        if valid:
            draft["travellers"] = to_json(rows)
            flow.save_side(draft, side)
            save_draft(request, draft)
            return redirect(_step_url(flow, 3))
        return render(
            request,
            f"{flow.template_prefix}_2.html",
            _traveller_context(flow, draft, formset, side, missing=missing),
            status=422,
        )
    initial = draft["travellers"] or [{}]
    formset = formset_class(initial=initial)
    side = flow.side_forms(None, draft, bound=False)
    return render(
        request, f"{flow.template_prefix}_2.html", _traveller_context(flow, draft, formset, side)
    )


def _step_confirm(
    request: HttpRequest, actor: Actor, flow: FlowDef, draft: dict[str, Any]
) -> HttpResponse:
    done: dict[str, str] = request.session.get(DONE_FLOWS, {})
    if draft["token"] in done:
        return redirect(done[draft["token"]])
    pricing_form: forms.Form | None = None
    if flow.pricing_step == 3:
        pricing_form = (
            flow.pricing_form(request.POST, **flow.pricing_kwargs(draft))
            if request.method == "POST"
            else flow.pricing_form(initial=draft["pricing"], **flow.pricing_kwargs(draft))
        )
    if request.method == "POST":
        if request.POST.get("action") == "confirm":
            if pricing_form is not None:
                if not pricing_form.is_valid():
                    return _render_confirm(request, actor, flow, draft, pricing_form, 422)
                draft["pricing"] = to_json(pricing_form.cleaned_data)
                save_draft(request, draft)
            return _commit(request, actor, flow, draft, pricing_form)
        if pricing_form is not None and pricing_form.is_valid():
            draft["pricing"] = to_json(pricing_form.cleaned_data)
            save_draft(request, draft)
    return _render_confirm(request, actor, flow, draft, pricing_form, 200)


def _render_confirm(
    request: HttpRequest,
    actor: Actor,
    flow: FlowDef,
    draft: dict[str, Any],
    pricing_form: forms.Form | None,
    status: int,
) -> HttpResponse:
    totals = flow.totals(draft)
    specs = flow.lines(draft) if draft["pricing"] else []
    context = _layout(
        flow,
        3,
        title=_title(flow),
        subtitle=flow.subtitle(draft),
        back_url=_step_url(flow, 2),
        cta=flow.confirm_label(draft),
        footer_label="Total client",
        footer_total=totals.price_xaf if draft["pricing"] else flow.step2_total(draft),
        draft=draft,
        pricing_form=pricing_form,
        totals=totals,
        specs=specs,
        checks=flow.checks(draft) if draft["pricing"] else [],
        ledger=flow.ledger(draft) if draft["pricing"] else [],
        is_manager=actor.can_view_financials,
        **flow.confirm_context(draft),
    )
    return render(request, f"{flow.template_prefix}_3.html", context, status=status)


def _commit(
    request: HttpRequest,
    actor: Actor,
    flow: FlowDef,
    draft: dict[str, Any],
    pricing_form: forms.Form | None,
) -> HttpResponse:
    """Crée le client, le dossier et toutes les lignes d'un seul bloc, puis émet chaque ligne."""
    specs = flow.lines(draft)
    name, phone = flow.customer(draft)
    departure = draft["trip"].get("departure_date") or None
    today = timezone.localdate()

    def create() -> UUID:
        customer = CrmService.find_or_create_customer(actor, name=name, phone=phone)
        case_id = CasesService.create_case(
            actor,
            customer_id=customer.id,
            departure_date=date.fromisoformat(departure) if departure else None,
        )
        for spec in specs:
            try:
                line = CasesService.add_line(
                    actor,
                    case_id=case_id,
                    kind=spec.kind,
                    label=spec.label,
                    price_xaf=spec.price_xaf,
                    cost_xaf=spec.cost_xaf,
                    passenger_name=spec.passenger_name,
                    ticket_number=spec.ticket_number,
                    carrier=spec.carrier,
                    details=spec.details,
                )
            except IntegrityError as error:
                raise InvalidLine(
                    f"Le billet {spec.ticket_number} existe déjà dans l'agence."
                ) from error
            if spec.cost_xaf is not None:
                CasesService.issue_line(actor, line_id=line.id, issued_on=today)
        return case_id

    case_id = attempt(request, create)
    if case_id is None:  # refus du domaine : le brouillon reste intact, le message l'explique
        return _render_confirm(request, actor, flow, draft, pricing_form, 422)
    target = reverse("web:flow_pay", kwargs={"case_id": case_id})
    done: dict[str, str] = request.session.get(DONE_FLOWS, {})
    done[draft["token"]] = target
    request.session[DONE_FLOWS] = dict(list(done.items())[-20:])
    clear_draft(request, flow.mode.slug)
    return redirect(target)


# --- étape 4 : paiement, étape 5 : remise --------------------------------------------------


class FlowPaymentForm(WebForm):
    method = forms.ChoiceField(
        label="Mode",
        choices=[
            (PaymentMethod.CASH.value, PaymentMethod.CASH.label),
            (PaymentMethod.MOBILE_MONEY.value, PaymentMethod.MOBILE_MONEY.label),
            (PaymentMethod.TRANSFER.value, PaymentMethod.TRANSFER.label),
        ],
        widget=forms.RadioSelect,
    )
    amount_xaf = forms.IntegerField(
        label="Montant (FCFA)",
        min_value=1,
        max_value=10_000_000_000,
        localize=False,
        widget=forms.NumberInput(attrs={"class": "money", "inputmode": "numeric", "step": 1}),
    )
    received_on = date_field("Date de réception")
    reference = forms.CharField(label="Référence de la transaction", max_length=64, required=False)
    given_xaf = forms.IntegerField(
        label="Montant remis par le client (FCFA)",
        min_value=0,
        required=False,
        localize=False,
        widget=forms.NumberInput(attrs={"class": "money", "inputmode": "numeric", "step": 1}),
    )
    idempotency_key = forms.CharField(widget=forms.HiddenInput, max_length=64)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["method"].initial = PaymentMethod.MOBILE_MONEY.value
        self.fields["received_on"].initial = timezone.localdate
        self.fields["idempotency_key"].initial = lambda: uuid.uuid4().hex


def _mode_of(detail: CaseDetail) -> FlowDef:
    for line in detail.lines:
        found = MODE_BY_KIND.get(line.kind)
        if found is not None and found.slug in FLOWS:
            return FLOWS[found.slug]
    return FLOWS["air"]


def _case_or_404(actor: Actor, case_id: UUID) -> CaseDetail:
    try:
        return CasesService.get_case(actor, case_id)
    except CaseNotFound as error:
        raise Http404 from error


@agency_required
@require_http_methods(["GET", "POST"])
def flow_pay(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    detail = _case_or_404(actor, case_id)
    flow = _mode_of(detail)
    summary = detail.summary
    done_url = reverse("web:flow_done", kwargs={"case_id": case_id})
    due = max(summary.balance_xaf, 0)
    form: FlowPaymentForm
    if request.method == "POST":
        if request.POST.get("action") == "skip":
            return redirect(done_url)
        form = FlowPaymentForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            recorded = attempt(
                request,
                lambda: PaymentsService.record_payment(
                    actor,
                    case_id=case_id,
                    method=PaymentMethod(data["method"]),
                    amount_xaf=data["amount_xaf"],
                    reference=data["reference"],
                    received_on=data["received_on"],
                    idempotency_key=f"flow:{uuid.uuid5(case_id, data['idempotency_key']).hex}",
                ),
                "Encaissement enregistré.",
            )
            if recorded is not None:
                return redirect(done_url)
    else:
        form = FlowPaymentForm(initial={"amount_xaf": due or None})
    paid = summary.price_total_xaf - summary.balance_xaf
    context = _layout(
        flow,
        4,
        title=f"Dossier {summary.reference} · {flow.mode.label}",
        subtitle=f"Vente confirmée · {summary.customer_name}",
        back_url=reverse("web:case_detail", kwargs={"case_id": case_id}),
        cta="Enregistrer l'encaissement",
        footer_label="À enregistrer",
        footer_total=due,
        form=form,
        summary=summary,
        paid=paid,
        due=due,
        departure=summary.departure_date,
        schedule=flow.schedule(summary.price_total_xaf, summary.departure_date),
        payments=PaymentsService.payments_for_case(actor, case_id),
        skip_url=done_url,
    )
    status = 422 if request.method == "POST" and form.errors else 200
    return render(request, "web/flow/pay.html", context, status=status)


def _banner(lines: list[Any], paid: int) -> str:
    issued = sum(1 for line in lines if line.issued_on is not None)
    title = f"{issued} billet{'s' if issued > 1 else ''} émis" if issued else "Dossier créé"
    if paid > 0:
        title += " · " + f"{paid:,}".replace(",", "\u202f") + "\u00a0FCFA encaissés"
    return title


@agency_required
@require_GET
def flow_done(request: HttpRequest, case_id: UUID) -> HttpResponse:
    actor = _actor(request)
    detail = _case_or_404(actor, case_id)
    flow = _mode_of(detail)
    summary = detail.summary
    customer = CrmService.get_customer(actor, summary.customer_id)
    agency = TenancyService.agency_info(actor).name
    paid = summary.price_total_xaf - summary.balance_xaf
    lines = [line for line in detail.lines if not line.is_voided]
    message = flow.message(detail, customer.name, agency, max(summary.balance_xaf, 0))
    context = _layout(
        flow,
        5,
        title=f"Dossier {summary.reference} · {flow.mode.label}",
        subtitle=f"{customer.name}"
        + (f" · départ le {summary.departure_date:%d/%m/%Y}" if summary.departure_date else ""),
        back_url=reverse("web:flow_pay", kwargs={"case_id": case_id}),
        cta="Voir le dossier",
        summary=summary,
        customer=customer,
        lines=lines,
        paid=paid,
        due=max(summary.balance_xaf, 0),
        message=message,
        banner_title=_banner(lines, paid),
        done_partial=f"web/flow/_done_{flow.mode.slug}.html",
        whatsapp=flow.whatsapp_link(customer.phone, message),
        is_manager=actor.can_view_financials,
        case_url=reverse("web:case_detail", kwargs={"case_id": case_id}),
        **flow.done_context(detail),
    )
    return render(request, "web/flow/done.html", context)
