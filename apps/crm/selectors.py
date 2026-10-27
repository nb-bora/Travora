from uuid import UUID

from apps.crm.dto import CustomerInfo
from apps.crm.exceptions import CustomerNotFound
from apps.crm.models import Customer


def to_info(customer: Customer) -> CustomerInfo:
    return CustomerInfo(id=customer.id, name=customer.name, phone=customer.phone)


def get_customer(customer_id: UUID) -> CustomerInfo:
    customer = Customer.objects.filter(id=customer_id).first()
    if customer is None:
        raise CustomerNotFound(str(customer_id))
    return to_info(customer)


def list_customers() -> list[CustomerInfo]:
    return [to_info(customer) for customer in Customer.objects.order_by("name", "id")]
