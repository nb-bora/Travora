import pytest

from apps.crm.exceptions import CustomerNotFound, InvalidPhoneNumber
from apps.crm.phone import normalize_phone
from apps.crm.services.public import CrmService
from apps.tenancy.services.public import TenancyService
from tests.conftest import AgencyFixture, runtime_role


@pytest.mark.parametrize(
    ("raw", "default", "expected"),
    [
        ("+237 677 12 34 56", "", "+237677123456"),
        ("00237677123456", "", "+237677123456"),
        ("(+33) 6.12.34.56.78", "", "+33612345678"),
        ("0677123456", "+237", "+237677123456"),
        ("", "", ""),
    ],
)
def test_phone_numbers_are_normalized_to_e164(raw: str, default: str, expected: str) -> None:
    assert normalize_phone(raw, default) == expected


@pytest.mark.parametrize("raw", ["677123456", "+0123456789", "+12", "abc", "+2376771234567890123"])
def test_phone_numbers_without_a_valid_international_form_are_refused(raw: str) -> None:
    with pytest.raises(InvalidPhoneNumber):
        normalize_phone(raw)


def test_a_customer_is_found_again_by_phone(agency_a: AgencyFixture) -> None:
    with TenancyService.scope(agency_a.id):
        first = CrmService.find_or_create_customer(
            agency_a.agent, name="Marie Ndong", phone="+237677123456"
        )
        again = CrmService.find_or_create_customer(
            agency_a.manager, name="M. Ndong", phone="+237 677 12 34 56"
        )
        assert again.id == first.id
        assert len(CrmService.list_customers(agency_a.agent)) == 1


def test_customers_without_phone_are_never_merged(agency_a: AgencyFixture) -> None:
    with TenancyService.scope(agency_a.id):
        one = CrmService.find_or_create_customer(agency_a.agent, name="Paul", phone="")
        two = CrmService.find_or_create_customer(agency_a.agent, name="Paul", phone="")
        assert one.id != two.id


def test_the_same_phone_can_exist_in_two_agencies(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_a.id):
        a = CrmService.find_or_create_customer(agency_a.agent, name="Alice", phone="+237677000001")
    with TenancyService.scope(agency_b.id):
        b = CrmService.find_or_create_customer(agency_b.agent, name="Alice", phone="+237677000001")
    assert a.id != b.id


def test_a_customer_of_another_agency_is_not_reachable(
    agency_a: AgencyFixture, agency_b: AgencyFixture
) -> None:
    with TenancyService.scope(agency_b.id):
        foreign = CrmService.find_or_create_customer(
            agency_b.agent, name="Autre", phone="+237677000002"
        )
    with runtime_role(), TenancyService.scope(agency_a.id):
        with pytest.raises(CustomerNotFound):
            CrmService.get_customer(agency_a.agent, foreign.id)
        assert CrmService.list_customers(agency_a.agent) == []
