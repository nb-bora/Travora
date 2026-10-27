"""Façade publique de l'application crm."""

from uuid import UUID

from apps.crm import selectors
from apps.crm.dto import CustomerInfo
from apps.crm.services import commands
from apps.shared_kernel.actor import Actor


class CrmService:
    @staticmethod
    def find_or_create_customer(
        actor: Actor, *, name: str, phone: str, default_country_code: str = ""
    ) -> CustomerInfo:
        return commands.find_or_create_customer(
            name=name, phone=phone, default_country_code=default_country_code
        )

    @staticmethod
    def get_customer(actor: Actor, customer_id: UUID) -> CustomerInfo:
        return selectors.get_customer(customer_id)

    @staticmethod
    def list_customers(actor: Actor) -> list[CustomerInfo]:
        return selectors.list_customers()
