from django.db import IntegrityError, transaction

from apps.crm.dto import CustomerInfo
from apps.crm.models import Customer
from apps.crm.phone import normalize_phone
from apps.crm.selectors import to_info


def find_or_create_customer(
    *, name: str, phone: str, default_country_code: str = ""
) -> CustomerInfo:
    """Retrouve le client par son téléphone dans l'agence, sinon le crée."""
    normalized = normalize_phone(phone, default_country_code)
    if normalized:
        existing = Customer.objects.filter(phone=normalized).first()
        if existing is not None:
            return to_info(existing)
    try:
        with transaction.atomic():
            customer = Customer.objects.create(name=name.strip(), phone=normalized)
    except IntegrityError:
        customer = Customer.objects.get(phone=normalized)
    return to_info(customer)
