"""Run offline LLM tests without application assembly, settings or real clients.

From backend:
    .venv/bin/python tests/run_llm_tests.py
    .venv/bin/python tests/run_llm_tests.py tests/unit/llm_router/test_llm_router.py -q

An explicit test path replaces the default tests/isolated_llm target; options
alone (for example -q or -k parser) keep that safe default. Real
schemas, dataclasses, services, parsers and tracking decorators are imported from
disk; only package initializers and infrastructure leaves are replaced here.
"""

import os
import sys
from datetime import UTC
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Do not let developer tracing configuration send test payloads to LangSmith.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


def package(name: str) -> None:
    module = ModuleType(name)
    module.__path__ = [str(ROOT.joinpath(*name.split(".")))]
    sys.modules[name] = module


def stub(name: str, **attributes: object) -> None:
    module = ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module


class UnavailableClient:
    """An infrastructure placeholder, never a working service client."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("Isolated LLM tests must supply a mock client")

    def __getattr__(self, name):
        raise AssertionError(f"Infrastructure access is forbidden: {name}")


for name in (
    "src",
    "src.core",
    "src.shared",
    "src.shared.application",
    "src.shared.domain",
    "src.shared.utils",
    "src.shared.infra",
    "src.shared.infra.services",
    "src.llm_service",
    "src.llm_router",
    "src.llm_router.domain",
    "src.llm_router.infra",
):
    package(name)

stub(
    "src.core.settings",
    settings=SimpleNamespace(image_ai_model="isolated-image-model"),
    timezone=UTC,
)
stub("src.core.providers", aitunnel_config=SimpleNamespace(key="unused-test-key"))
stub("src.core.redis", redis_client=UnavailableClient.__new__(UnavailableClient))
stub("src.llm_router.infra.repository", SqlAIModelRepository=UnavailableClient)
stub("src.llm_router.infra.external_apis", MediaClient=UnavailableClient)
sys.modules["src.shared.infra.services"].SrvBaseClient = UnavailableClient

import pytest  # noqa: E402

if __name__ == "__main__":
    arguments = sys.argv[1:]
    has_target = any(
        not argument.startswith("-") and (ROOT / argument.split("::", 1)[0]).exists()
        for argument in arguments
    )
    targets = [] if has_target else [str(ROOT / "tests/isolated_llm")]
    raise SystemExit(
        pytest.main(
            [
                "-p",
                "pytest_asyncio.plugin",
                "--confcutdir",
                str(ROOT / "tests"),
                *targets,
                *(arguments or ["-q"]),
            ]
        )
    )
