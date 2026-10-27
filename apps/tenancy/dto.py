from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AgencyInfo:
    id: UUID
    name: str
    slug: str
    logo_path: str
