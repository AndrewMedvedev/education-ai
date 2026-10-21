"""Проверки provisioning-файлов без приложения, БД и LLM."""

import json
import re
from pathlib import Path

import pytest

DASHBOARDS = Path(__file__).resolve().parents[4] / "monitoring/grafana/dashboards"
FILES = sorted(DASHBOARDS.glob("*.json"))
GRID_COLUMNS = 24
PERCENTILE_COUNT = 3


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.stem)
def test_dashboard_has_sections_unique_ids_and_no_overlapping_panels(path):
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    panels = dashboard["panels"]
    ids = [panel["id"] for panel in panels]
    assert len(ids) == len(set(ids))
    assert any(panel["type"] == "row" for panel in panels)
    for index, panel in enumerate(panels):
        box = panel["gridPos"]
        assert 0 <= box["x"] < GRID_COLUMNS
        assert box["x"] + box["w"] <= GRID_COLUMNS
        assert box["y"] >= 0
        for other in panels[index + 1 :]:
            other_box = other["gridPos"]
            assert (
                box["x"] + box["w"] <= other_box["x"]
                or other_box["x"] + other_box["w"] <= box["x"]
                or box["y"] + box["h"] <= other_box["y"]
                or other_box["y"] + other_box["h"] <= box["y"]
            ), (path.stem, panel["title"], other["title"])


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.stem)
def test_queries_use_configured_sources_and_scope_container_resources(path):
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    allowed_sources = {"prometheus_main", "loki_main", "llm_postgres"}
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            source = target.get("datasource", panel.get("datasource"))
            assert source["uid"] in allowed_sources
            expression = target.get("expr", "")
            if "container_label_com_docker_compose_service" in expression:
                project_filter = (
                    'container_label_com_docker_compose_project=~"dio-ai-courses(-local)?"'
                )
                assert project_filter in expression
            if target.get("rawSql"):
                assert "public.llm_invocations" in target["rawSql"]
                assert "deleted_at IS NULL" in target["rawSql"]


def test_llm_keeps_trace_relationship_and_does_not_invent_usage_or_cost():
    dashboard = json.loads((DASHBOARDS / "llm-router.json").read_text(encoding="utf-8"))
    queries = [
        target["rawSql"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if target.get("rawSql")
    ]
    assert any("GROUP BY request_id" in query for query in queries)
    assert any("request_id = (SELECT request_id" in query for query in queries)
    assert any("jsonb_pretty(request)" in query for query in queries)
    assert any("jsonb_pretty(response)" in query for query in queries)
    assert all("input_tokens" not in query and "output_tokens" not in query for query in queries)
    assert all("cost" not in query and "price" not in query for query in queries)


def test_taskiq_percentiles_do_not_report_fake_ten_second_cap():
    dashboard = json.loads((DASHBOARDS / "taskiq.json").read_text(encoding="utf-8"))
    percentiles = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if "histogram_quantile" in target.get("expr", "")
    ]
    assert len(percentiles) == PERCENTILE_COUNT
    assert all('le="10.0"' in expression for expression in percentiles)
    assert all("and on(task_name)" in expression for expression in percentiles)


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.stem)
def test_metric_legends_are_explicit_and_loki_uses_supported_interval(path):
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            expression = target.get("expr", "")
            if not expression:
                continue
            if panel["type"] != "logs":
                legend = target.get("legendFormat", "").strip()
                assert legend, (path.stem, panel["title"])
                assert legend != expression, (path.stem, panel["title"])
            source = target.get("datasource", panel.get("datasource"))
            if source["type"] == "loki":
                assert "$__rate_interval" not in expression
                if "$__interval" in expression:
                    assert panel["interval"] == "1m"


@pytest.mark.parametrize(
    ("dashboard_name", "original", "expected"),
    [
        ("qdrant", "P95 /collections/{collection_name}/points/count", "P95 Подсчёт точек"),
        ("qdrant", "P50 /qdrant.Points/Count", "P50 Подсчёт точек"),
        ("taskiq", "monitoring_smoke:smoke_success", "Тест: успешная задача"),
        (
            "taskiq",
            "Успех — monitoring_smoke:smoke_success",
            "Успех — Тест: успешная задача",
        ),
        (
            "taskiq",
            "src.courses.agents.course_generator.workflow:generate_course",
            "Генерация курса",
        ),
    ],
)
def test_operation_legends_are_readable(dashboard_name, original, expected):
    dashboard = json.loads((DASHBOARDS / f"{dashboard_name}.json").read_text(encoding="utf-8"))
    panels = [
        panel
        for panel in dashboard["panels"]
        if any(
            "{{endpoint}}" in target.get("legendFormat", "")
            or "{{task_name}}" in target.get("legendFormat", "")
            for target in panel.get("targets", [])
        )
    ]
    assert panels
    for panel in panels:
        label = original
        for transformation in panel.get("transformations", []):
            if transformation["id"] == "renameByRegex":
                options = transformation["options"]
                # Без разделителей Grafana добавляет ^...$ и теряет совпадения с префиксом.
                pattern = options["regex"]
                assert pattern.startswith("/")
                assert pattern.endswith("/")
                label = re.sub(pattern[1:-1], options["renamePattern"], label)
        assert label == expected, panel["title"]
