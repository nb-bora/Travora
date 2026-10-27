import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "check_licenses.py"
spec = importlib.util.spec_from_file_location("check_licenses", SCRIPT)
assert spec is not None
assert spec.loader is not None
check_licenses = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_licenses)


@pytest.mark.parametrize(
    "text",
    [
        "GNU Affero General Public License v3 (AGPLv3)",
        "AGPL-3.0-or-later",
        "GNU General Public License v3 (GPLv3)",
        "GPL-2.0-only",
        "Server Side Public License",
        "SSPL-1.0",
        "BUSL-1.1",
        "Business Source License 1.1",
    ],
)
def test_licenses_incompatible_with_a_closed_saas_are_refused(text: str) -> None:
    assert check_licenses.is_forbidden(text)


@pytest.mark.parametrize(
    "text",
    [
        "MIT License",
        "BSD-3-Clause",
        "Apache-2.0",
        "ISC License (ISCL)",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "GNU Lesser General Public License v3 (LGPLv3)",
        "LGPL-3.0-or-later",
        "Historical Permission Notice and Disclaimer (HPND)",
    ],
)
def test_permissive_and_weak_copyleft_licenses_are_accepted(text: str) -> None:
    assert not check_licenses.is_forbidden(text)
