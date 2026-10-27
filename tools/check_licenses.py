"""Refuse les dépendances sous licence incompatible avec un SaaS fermé.

Interdites : AGPL, GPL, SSPL, BSL. La LGPL est acceptée (liaison dynamique non modifiée).
Usage : python tools/check_licenses.py, dans l'environnement des dépendances de production.
"""

import sys
from importlib.metadata import Distribution, distributions

ALWAYS_FORBIDDEN = ("AGPL", "AFFERO", "SSPL", "SERVER SIDE PUBLIC", "BUSL", "BUSINESS SOURCE")


def license_text(dist: Distribution) -> str:
    metadata = dist.metadata
    parts = [
        metadata.get("License-Expression") or "",
        metadata.get("License") or "",
        *(c for c in (metadata.get_all("Classifier") or []) if c.startswith("License ::")),
    ]
    return " | ".join(part for part in parts if part)


def is_forbidden(text: str) -> bool:
    upper = text.upper()
    if any(word in upper for word in ALWAYS_FORBIDDEN):
        return True
    mentions_gpl = "GPL" in upper or "GENERAL PUBLIC LICENSE" in upper
    return mentions_gpl and "LGPL" not in upper and "LESSER" not in upper


def main() -> int:
    forbidden = []
    unknown = []
    installed = sorted(distributions(), key=lambda d: (d.metadata.get("Name") or "").lower())
    for dist in installed:
        name = dist.metadata.get("Name") or "?"
        text = license_text(dist)
        if not text:
            unknown.append(name)
        elif is_forbidden(text):
            forbidden.append(f"{name} : {text[:120]}")
    for name in unknown:
        print(f"licence non déclarée : {name}")
    for line in forbidden:
        print(f"LICENCE INTERDITE : {line}")
    print(f"{len(installed)} paquets examinés, {len(forbidden)} licence(s) interdite(s).")
    return 1 if forbidden else 0


if __name__ == "__main__":
    sys.exit(main())
