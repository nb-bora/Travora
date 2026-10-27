from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CustomerInfo:
    id: UUID
    name: str
    phone: str
