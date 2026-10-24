"""Run invitation tests without importing unrelated application routers.

Usage (from backend): python tests/run_invitation_tests.py
The src package normally assembles the whole application during import. Only
that assembly and the API router discovery are skipped; tested modules and
their dependencies remain real. No database or mail service is contacted.
"""

import os
import sys
import types
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ["APP_NAME"] = "Invitation tests"
os.environ["APP_VERSION"] = "test"
for service in ["IAM", "ORGANIZATION", "COURSE"]:
    os.environ[f"SRV_{service}_BASE_URL"] = "http://127.0.0.1:8000"
    os.environ[f"SRV_{service}_CLIENT_ID"] = "unit-test"
    os.environ[f"SRV_{service}_CLIENT_SECRET"] = "unit-test"
for name in ["src", "src.iam.api.v1", "src.organization.api.v1"]:
    package = types.ModuleType(name)
    package.__path__ = [str(root.joinpath(*name.split(".")))]
    sys.modules[name] = package

import pytest  # noqa: E402

raise SystemExit(
    pytest.main(
        [
            str(root / "tests/unit/iam/test_invitation_registration.py"),
            str(root / "tests/unit/iam/test_organization_invitation_management.py"),
            "-q",
            *sys.argv[1:],
        ]
    )
)
