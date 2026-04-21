"""Tech Debt scanner — unit tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

from tech_debt import scan_project, score_roi  # noqa: E402
from tech_debt.scanner import DebtItem  # noqa: E402
from tech_debt.spec_generator import generate_spec_from_item  # noqa: E402


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    # Python file with TODO, long function, stale dep
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text(
        "# TODO: refactor this monster\n"
        "def big():\n"
        + "    x = 1\n" * 70
        + "    return x\n",
        encoding="utf-8",
    )
    (src / "b.py").write_text(
        "# FIXME: race condition suspected\n"
        "def ok():\n"
        "    return 42\n",
        encoding="utf-8",
    )
    # Duplicated block across two files
    dup = (
        "value = 1\n"
        "value = value + 2\n"
        "value = value * 3\n"
        "value = value - 1\n"
        "value = value // 2\n"
        "value = value + 10\n"
        "return value\n"
    )
    (src / "c.py").write_text(f"def c_fn():\n{dup}", encoding="utf-8")
    (src / "d.py").write_text(f"def d_fn():\n{dup}", encoding="utf-8")

    (tmp_path / "requirements.txt").write_text(
        "requests\npytest==8.0.0\n", encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"old-lib": "^0.1.0"}}),
        encoding="utf-8",
    )
    return tmp_path


def test_scan_detects_multiple_kinds(sample_project):
    report = scan_project(sample_project)
    kinds = {i.kind for i in report.items}
    assert "todo_fixme" in kinds
    assert "long_function" in kinds
    assert "stale_deps" in kinds
    assert "duplication" in kinds


def test_items_sorted_by_roi_desc(sample_project):
    report = scan_project(sample_project)
    rois = [i.roi for i in report.items]
    assert rois == sorted(rois, reverse=True)


def test_score_roi_formula():
    assert score_roi(10, 2) == 5.0
    assert score_roi(1, 0) == 10  # effort 0 fallback


def test_fixme_scores_higher_than_todo(sample_project):
    report = scan_project(sample_project)
    todos = [i for i in report.items if i.kind == "todo_fixme"]
    fixme_roi = max((i.roi for i in todos if "fixme" in i.tags), default=0)
    todo_roi = max(
        (i.roi for i in todos if "todo" in i.tags and "fixme" not in i.tags),
        default=0,
    )
    assert fixme_roi > todo_roi


def test_persists_last_report_and_trend(sample_project):
    report = scan_project(sample_project)
    snapshot = sample_project / ".workpilot" / "tech_debt" / "last_report.json"
    trend = sample_project / ".workpilot" / "tech_debt" / "trend.json"
    assert snapshot.exists()
    assert trend.exists()
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == len(report.items)
    trend_payload = json.loads(trend.read_text(encoding="utf-8"))
    assert len(trend_payload) >= 1


def test_scan_twice_appends_trend(sample_project):
    scan_project(sample_project)
    report2 = scan_project(sample_project)
    assert len(report2.trend) == 2


def test_missing_project_rejected(tmp_path):
    with pytest.raises(ValueError):
        scan_project(tmp_path / "does-not-exist")


def test_generate_spec_from_item(tmp_path: Path):
    item = DebtItem(
        id="abc123",
        kind="todo_fixme",
        file_path="src/a.py",
        line=5,
        message="refactor auth guard",
        cost=2.0,
        effort=1.0,
        roi=2.0,
        tags=["fixme"],
        context="# FIXME: refactor auth guard",
    )
    spec_dir = generate_spec_from_item(tmp_path, item, llm_hint="Extract helper.")
    assert spec_dir.exists()
    spec_md = spec_dir / "spec.md"
    source = spec_dir / "source.json"
    assert spec_md.exists()
    body = spec_md.read_text(encoding="utf-8")
    assert "refactor auth guard" in body
    assert "Extract helper." in body
    payload = json.loads(source.read_text(encoding="utf-8"))
    assert payload["id"] == "abc123"
