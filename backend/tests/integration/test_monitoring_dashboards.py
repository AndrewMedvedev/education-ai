"""Read-only проверка всех запросов Grafana на явно указанном тестовом стенде."""

import json
import os
from pathlib import Path
from time import time

import httpx
import pytest

DASHBOARDS = Path(__file__).resolve().parents[3] / "monitoring/grafana/dashboards"
TARGETS = [
    (path.stem, panel["title"], target)
    for path in DASHBOARDS.glob("*.json")
    for panel in json.loads(path.read_text(encoding="utf-8"))["panels"]
    for target in panel.get("targets", [])
    if target.get("expr")
]
SQL_TARGETS = [
    target
    for panel in json.loads((DASHBOARDS / "llm-router.json").read_text(encoding="utf-8"))["panels"]
    for target in panel.get("targets", [])
    if target.get("rawSql")
]


@pytest.mark.skipif(not os.getenv("TEST_GRAFANA_URL"), reason="Explicit Grafana URL required")
@pytest.mark.parametrize(
    ("dashboard", "panel", "target"), TARGETS, ids=[f"{d}-{p}-{t['refId']}" for d, p, t in TARGETS]
)
def test_dashboard_query(dashboard, panel, target):
    now = int(time() * 1000)
    expr = target["expr"]
    source_type = target["datasource"]["type"]
    if source_type == "loki":
        assert "$__rate_interval" not in expr, "Loki does not support Prometheus rate interval"
    else:
        expr = expr.replace("$__rate_interval", "5m")
    for variable, value in {
        "$__interval": "1m",
        "$__range": "1h",
        "${container_service:regex}": ".+",
        "${job:regex}": ".*",
    }.items():
        expr = expr.replace(variable, value)
    if os.getenv("TEST_TASKIQ_QUEUE"):
        # Проверяем ту же панель на изолированной очереди, не читаем боевые задачи.
        expr = expr.replace('queue="courses.taskiq"', f'queue="{os.environ["TEST_TASKIQ_QUEUE"]}"')
    query = {
        **target,
        "refId": "A",
        "datasource": target["datasource"],
        "expr": expr,
        "instant": True,
        "range": False,
        "intervalMs": 15000,
        "maxDataPoints": 200,
    }
    if target["datasource"]["type"] == "loki":
        query.update(queryType="range", direction="backward")
    response = httpx.post(
        f"{os.environ['TEST_GRAFANA_URL']}/api/ds/query",
        auth=(os.environ["TEST_GRAFANA_USER"], os.environ["TEST_GRAFANA_PASSWORD"]),
        json={"from": str(now - 3600000), "to": str(now), "queries": [query]},
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()["results"]["A"]
    assert not result.get("error"), f"{dashboard}/{panel}: {result.get('error')}"
    assert result["status"] == httpx.codes.OK
    if target["datasource"]["type"] == "prometheus":
        # NoData нельзя считать успешно проверенной метрикой.
        assert any(
            values for frame in result.get("frames", []) for values in frame["data"]["values"]
        ), f"{dashboard}/{panel}: metric returned no samples"


@pytest.mark.skipif(not os.getenv("TEST_GRAFANA_URL"), reason="Explicit Grafana URL required")
@pytest.mark.parametrize("target", SQL_TARGETS)
def test_llm_dashboard_sql(target):
    now = int(time() * 1000)
    selected_id = (
        "(SELECT id::text FROM public.llm_invocations WHERE deleted_at IS NULL "
        "ORDER BY created_at DESC, id DESC LIMIT 1)"
    )
    query = {
        **target,
        "refId": "A",
        "datasource": {"type": "postgres", "uid": "llm_postgres"},
        "rawSql": target["rawSql"].replace("${invocation_id:sqlstring}", selected_id),
        "format": "table",
    }
    response = httpx.post(
        f"{os.environ['TEST_GRAFANA_URL']}/api/ds/query",
        auth=(os.environ["TEST_GRAFANA_USER"], os.environ["TEST_GRAFANA_PASSWORD"]),
        json={"from": str(now - 7 * 86400000), "to": str(now), "queries": [query]},
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()["results"]["A"]
    assert not result.get("error"), result.get("error")
    assert result["status"] == httpx.codes.OK
