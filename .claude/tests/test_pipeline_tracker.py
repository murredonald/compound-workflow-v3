"""Tests for .claude/tools/pipeline_tracker.py — pipeline progress tracker."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pipeline_tracker import (
    EVOLUTION_PHASES,
    GREENFIELD_PHASES,
    add_phase,
    complete_phase,
    get_current,
    init_pipeline,
    load_pipeline,
    render_backlog_summary,
    render_dashboard,
    skip_phase,
    start_phase,
    task_update,
)


@pytest.fixture()
def status_file(tmp_path: Path) -> Path:
    """Return a temporary pipeline status file path (does not exist yet)."""
    return tmp_path / "pipeline-status.json"


@pytest.fixture()
def greenfield(status_file: Path) -> dict:
    """Initialize a greenfield pipeline and return the data."""
    return init_pipeline("greenfield", "Test Project", path=status_file)


@pytest.fixture()
def evolution(status_file: Path) -> dict:
    """Initialize an evolution pipeline and return the data."""
    return init_pipeline("evolution", "Test Project", path=status_file)


# ---------------------------------------------------------------------------
# init_pipeline
# ---------------------------------------------------------------------------


class TestInitPipeline:
    def test_creates_file(self, status_file: Path) -> None:
        init_pipeline("greenfield", "My App", path=status_file)
        assert status_file.exists()

    def test_greenfield_type(self, greenfield: dict) -> None:
        assert greenfield["pipeline_type"] == "greenfield"

    def test_evolution_type(self, evolution: dict) -> None:
        assert evolution["pipeline_type"] == "evolution"

    def test_project_name(self, greenfield: dict) -> None:
        assert greenfield["project_name"] == "Test Project"

    def test_greenfield_base_phases(self, greenfield: dict) -> None:
        ids = [p["id"] for p in greenfield["phases"]]
        assert "plan" in ids
        assert "synthesize" in ids
        assert "execute" in ids
        assert "retro" in ids
        assert "specialists/competition" in ids
        assert "plan-define" in ids

    def test_evolution_base_phases(self, evolution: dict) -> None:
        ids = [p["id"] for p in evolution["phases"]]
        assert "intake" in ids
        assert "plan-delta" in ids
        assert "synthesize" in ids
        assert "execute" in ids
        assert "retro" in ids

    def test_all_phases_pending(self, greenfield: dict) -> None:
        for phase in greenfield["phases"]:
            assert phase["status"] == "pending"

    def test_current_phase_none(self, greenfield: dict) -> None:
        assert greenfield["current_phase"] is None

    def test_timestamps_set(self, greenfield: dict) -> None:
        assert greenfield["started_at"] is not None
        assert greenfield["updated_at"] is not None

    def test_refuses_overwrite_without_force(self, status_file: Path) -> None:
        init_pipeline("greenfield", "First", path=status_file)
        with pytest.raises(SystemExit):
            init_pipeline("greenfield", "Second", path=status_file)

    def test_force_overwrites(self, status_file: Path) -> None:
        init_pipeline("greenfield", "First", path=status_file)
        data = init_pipeline("greenfield", "Second", path=status_file, force=True)
        assert data["project_name"] == "Second"

    def test_roundtrip(self, status_file: Path) -> None:
        init_pipeline("greenfield", "RT", path=status_file)
        loaded = load_pipeline(status_file)
        assert loaded["project_name"] == "RT"
        assert loaded["pipeline_type"] == "greenfield"


# ---------------------------------------------------------------------------
# start_phase
# ---------------------------------------------------------------------------


class TestStartPhase:
    def test_marks_in_progress(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "plan")
        assert phase["status"] == "in_progress"

    def test_sets_current_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        assert data["current_phase"] == "plan"

    def test_sets_started_at(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "plan")
        assert phase["started_at"] is not None

    def test_rejects_completed_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        with pytest.raises(SystemExit):
            start_phase("plan", path=status_file)

    def test_rejects_skipped_phase(self, status_file: Path, greenfield: dict) -> None:
        skip_phase("plan", path=status_file)
        with pytest.raises(SystemExit):
            start_phase("plan", path=status_file)

    def test_rejects_concurrent_in_progress(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        with pytest.raises(SystemExit):
            start_phase("synthesize", path=status_file)

    def test_rejects_unknown_phase(self, status_file: Path, greenfield: dict) -> None:
        with pytest.raises(SystemExit):
            start_phase("nonexistent", path=status_file)


# ---------------------------------------------------------------------------
# complete_phase
# ---------------------------------------------------------------------------


class TestCompletePhase:
    def test_marks_completed(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "plan")
        assert phase["status"] == "completed"

    def test_sets_completed_at(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "plan")
        assert phase["completed_at"] is not None

    def test_stores_summary(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", summary="9 decisions, Deep mode", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "plan")
        assert phase["summary"] == "9 decisions, Deep mode"

    def test_clears_current_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        data = load_pipeline(status_file)
        assert data["current_phase"] is None

    def test_rejects_pending_phase(self, status_file: Path, greenfield: dict) -> None:
        with pytest.raises(SystemExit):
            complete_phase("plan", path=status_file)

    def test_rejects_unknown_phase(self, status_file: Path, greenfield: dict) -> None:
        with pytest.raises(SystemExit):
            complete_phase("nonexistent", path=status_file)


# ---------------------------------------------------------------------------
# skip_phase
# ---------------------------------------------------------------------------


class TestSkipPhase:
    def test_marks_skipped(self, status_file: Path, greenfield: dict) -> None:
        skip_phase("specialists/competition", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "specialists/competition")
        assert phase["status"] == "skipped"

    def test_stores_reason(self, status_file: Path, greenfield: dict) -> None:
        skip_phase("specialists/competition", reason="not needed", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "specialists/competition")
        assert phase["summary"] == "Skipped: not needed"

    def test_rejects_completed_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        with pytest.raises(SystemExit):
            skip_phase("plan", path=status_file)

    def test_rejects_in_progress_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        with pytest.raises(SystemExit):
            skip_phase("plan", path=status_file)


# ---------------------------------------------------------------------------
# task_update
# ---------------------------------------------------------------------------


class TestTaskUpdate:
    def test_sets_execute_progress(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        start_phase("specialists/competition", path=status_file)
        complete_phase("specialists/competition", path=status_file)
        start_phase("plan-define", path=status_file)
        complete_phase("plan-define", path=status_file)
        start_phase("synthesize", path=status_file)
        complete_phase("synthesize", path=status_file)
        start_phase("execute", path=status_file)
        task_update(
            milestone="M2",
            task="T09",
            total_milestones=4,
            completed_milestones=1,
            total_tasks=25,
            completed_tasks=8,
            path=status_file,
        )
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "execute")
        ep = phase["execute_progress"]
        assert ep["current_milestone"] == "M2"
        assert ep["current_task"] == "T09"
        assert ep["total_milestones"] == 4
        assert ep["completed_tasks"] == 8

    def test_includes_labels(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        start_phase("specialists/competition", path=status_file)
        complete_phase("specialists/competition", path=status_file)
        start_phase("plan-define", path=status_file)
        complete_phase("plan-define", path=status_file)
        start_phase("synthesize", path=status_file)
        complete_phase("synthesize", path=status_file)
        start_phase("execute", path=status_file)
        task_update(
            milestone="M1",
            task="T03",
            total_milestones=3,
            completed_milestones=0,
            total_tasks=15,
            completed_tasks=2,
            milestone_label="Core Backend",
            task_label="User auth",
            path=status_file,
        )
        data = load_pipeline(status_file)
        ep = next(p for p in data["phases"] if p["id"] == "execute")["execute_progress"]
        assert ep["milestone_label"] == "Core Backend"
        assert ep["task_label"] == "User auth"


# ---------------------------------------------------------------------------
# add_phase
# ---------------------------------------------------------------------------


class TestAddPhase:
    def test_inserts_after_target(self, status_file: Path, greenfield: dict) -> None:
        add_phase("specialists/backend", "Backend Deep Dive", "plan-define", path=status_file)
        data = load_pipeline(status_file)
        ids = [p["id"] for p in data["phases"]]
        idx_define = ids.index("plan-define")
        idx_backend = ids.index("specialists/backend")
        assert idx_backend == idx_define + 1

    def test_new_phase_is_pending(self, status_file: Path, greenfield: dict) -> None:
        add_phase("specialists/backend", "Backend Deep Dive", "plan-define", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "specialists/backend")
        assert phase["status"] == "pending"

    def test_default_command(self, status_file: Path, greenfield: dict) -> None:
        add_phase("specialists/backend", "Backend Deep Dive", "plan-define", path=status_file)
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "specialists/backend")
        assert phase["command"] == "/specialists/backend"

    def test_custom_command(self, status_file: Path, greenfield: dict) -> None:
        add_phase(
            "specialists/backend", "Backend Deep Dive", "plan-define",
            command="/specialists/backend --deep", path=status_file,
        )
        data = load_pipeline(status_file)
        phase = next(p for p in data["phases"] if p["id"] == "specialists/backend")
        assert phase["command"] == "/specialists/backend --deep"

    def test_rejects_duplicate(self, status_file: Path, greenfield: dict) -> None:
        add_phase("specialists/backend", "Backend", "plan-define", path=status_file)
        with pytest.raises(SystemExit):
            add_phase("specialists/backend", "Backend Again", "plan-define", path=status_file)

    def test_rejects_unknown_after(self, status_file: Path, greenfield: dict) -> None:
        with pytest.raises(SystemExit):
            add_phase("specialists/backend", "Backend", "nonexistent", path=status_file)

    def test_multiple_inserts_preserve_order(self, status_file: Path, greenfield: dict) -> None:
        add_phase("specialists/domain", "Domain", "plan-define", path=status_file)
        add_phase("specialists/architecture", "Architecture", "specialists/domain", path=status_file)
        add_phase("specialists/backend", "Backend", "specialists/architecture", path=status_file)
        data = load_pipeline(status_file)
        ids = [p["id"] for p in data["phases"]]
        assert ids.index("specialists/domain") < ids.index("specialists/architecture")
        assert ids.index("specialists/architecture") < ids.index("specialists/backend")


# ---------------------------------------------------------------------------
# render_dashboard
# ---------------------------------------------------------------------------


class TestRenderDashboard:
    def test_contains_project_name(self, status_file: Path, greenfield: dict) -> None:
        output = render_dashboard(status_file)
        assert "Test Project" in output

    def test_contains_pipeline_type(self, status_file: Path, greenfield: dict) -> None:
        output = render_dashboard(status_file)
        assert "greenfield" in output

    def test_pending_markers(self, status_file: Path, greenfield: dict) -> None:
        output = render_dashboard(status_file)
        assert "[ ]" in output

    def test_completed_marker(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", summary="Done", path=status_file)
        output = render_dashboard(status_file)
        assert "[x]" in output
        assert "Done" in output

    def test_in_progress_marker(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        output = render_dashboard(status_file)
        assert "[>]" in output
        assert "In progress..." in output

    def test_skipped_marker(self, status_file: Path, greenfield: dict) -> None:
        skip_phase("specialists/competition", reason="not needed", path=status_file)
        output = render_dashboard(status_file)
        assert "[-]" in output
        assert "Skipped: not needed" in output

    def test_progress_counter(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        output = render_dashboard(status_file)
        assert "1/" in output
        assert "phases complete" in output

    def test_execute_progress_in_dashboard(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        start_phase("specialists/competition", path=status_file)
        complete_phase("specialists/competition", path=status_file)
        start_phase("plan-define", path=status_file)
        complete_phase("plan-define", path=status_file)
        start_phase("synthesize", path=status_file)
        complete_phase("synthesize", path=status_file)
        start_phase("execute", path=status_file)
        task_update(
            milestone="M2", task="T09",
            total_milestones=4, completed_milestones=1,
            total_tasks=25, completed_tasks=8,
            milestone_label="Core Backend", task_label="User auth endpoints",
            path=status_file,
        )
        output = render_dashboard(status_file)
        assert "M1/4 milestones" in output
        assert "8/25 tasks" in output
        assert "Current:" in output

    def test_idle_when_no_current(self, status_file: Path, greenfield: dict) -> None:
        output = render_dashboard(status_file)
        assert "Idle" in output


# ---------------------------------------------------------------------------
# get_current
# ---------------------------------------------------------------------------


class TestGetCurrent:
    def test_none_initially(self, status_file: Path, greenfield: dict) -> None:
        assert get_current(status_file) is None

    def test_returns_active_phase(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        assert get_current(status_file) == "plan"

    def test_none_after_complete(self, status_file: Path, greenfield: dict) -> None:
        start_phase("plan", path=status_file)
        complete_phase("plan", path=status_file)
        assert get_current(status_file) is None


# ---------------------------------------------------------------------------
# CLI (main via subprocess-like invocations)
# ---------------------------------------------------------------------------


class TestCLI:
    def test_help_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
        captured = capsys.readouterr()
        assert "pipeline" in captured.out.lower()

    def test_init_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["init", "--type", "greenfield", "--project", "Test"])
        assert args.command == "init"
        assert args.pipeline_type == "greenfield"
        assert args.project == "Test"

    def test_start_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["start", "--phase", "plan"])
        assert args.command == "start"
        assert args.phase == "plan"

    def test_complete_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["complete", "--phase", "plan", "--summary", "done"])
        assert args.command == "complete"
        assert args.summary == "done"

    def test_task_update_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "task-update",
            "--milestone", "M2", "--task", "T09",
            "--total-milestones", "4", "--completed-milestones", "1",
            "--total-tasks", "25", "--completed-tasks", "8",
        ])
        assert args.command == "task-update"
        assert args.total_milestones == 4

    def test_add_phase_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "add-phase", "--phase", "specialists/backend",
            "--label", "Backend", "--after", "plan-define",
        ])
        assert args.command == "add-phase"
        assert args.after_phase == "plan-define"

    def test_status_file_override(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["--status-file", "/tmp/test.json", "status"])
        assert args.status_file == Path("/tmp/test.json")

    def test_backlog_summary_subcommand_args(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["backlog-summary"])
        assert args.command == "backlog-summary"

    def test_backlog_summary_with_file_override(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["backlog-summary", "--backlog-file", "/tmp/backlog.md"])
        assert args.command == "backlog-summary"
        assert args.backlog_file == Path("/tmp/backlog.md")

    def test_backlog_summary_default_file(self) -> None:
        from pipeline_tracker import build_parser

        parser = build_parser()
        args = parser.parse_args(["backlog-summary"])
        assert args.backlog_file is None


# ---------------------------------------------------------------------------
# Phase Constants (v3.11)
# ---------------------------------------------------------------------------


class TestPhaseConstants:
    """Verify GREENFIELD_PHASES and EVOLUTION_PHASES have the expected phases."""

    def test_greenfield_has_release_phase(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert "release" in ids

    def test_greenfield_has_runtime_qa(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert "runtime-qa" in ids

    def test_greenfield_has_qa_fix_pass(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert "qa-fix-pass" in ids

    def test_greenfield_release_after_qa_fix(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert ids.index("release") > ids.index("qa-fix-pass")

    def test_greenfield_release_before_retro(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert ids.index("release") < ids.index("retro")

    def test_greenfield_phase_order(self) -> None:
        """Full expected order of greenfield base phases."""
        ids = [p["id"] for p in GREENFIELD_PHASES]
        expected_order = [
            "plan", "specialists/competition", "plan-define",
            "synthesize", "execute", "runtime-qa", "qa-fix-pass",
            "release", "retro",
        ]
        assert ids == expected_order

    def test_greenfield_release_command(self) -> None:
        release = next(p for p in GREENFIELD_PHASES if p["id"] == "release")
        assert release["command"] == "/release"

    def test_evolution_has_release_phase(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert "release" in ids

    def test_evolution_has_runtime_qa(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert "runtime-qa" in ids

    def test_evolution_has_qa_fix_pass(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert "qa-fix-pass" in ids

    def test_evolution_release_after_qa_fix(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert ids.index("release") > ids.index("qa-fix-pass")

    def test_evolution_release_before_retro(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert ids.index("release") < ids.index("retro")

    def test_evolution_phase_order(self) -> None:
        """Full expected order of evolution base phases."""
        ids = [p["id"] for p in EVOLUTION_PHASES]
        expected_order = [
            "intake", "plan-delta",
            "synthesize", "execute", "runtime-qa", "qa-fix-pass",
            "release", "retro",
        ]
        assert ids == expected_order

    def test_evolution_release_command(self) -> None:
        release = next(p for p in EVOLUTION_PHASES if p["id"] == "release")
        assert release["command"] == "/release"

    def test_all_greenfield_phases_have_required_keys(self) -> None:
        for phase in GREENFIELD_PHASES:
            assert "id" in phase, f"Missing 'id' in {phase}"
            assert "label" in phase, f"Missing 'label' in {phase}"
            assert "command" in phase, f"Missing 'command' in {phase}"

    def test_all_evolution_phases_have_required_keys(self) -> None:
        for phase in EVOLUTION_PHASES:
            assert "id" in phase, f"Missing 'id' in {phase}"
            assert "label" in phase, f"Missing 'label' in {phase}"
            assert "command" in phase, f"Missing 'command' in {phase}"

    def test_no_duplicate_greenfield_ids(self) -> None:
        ids = [p["id"] for p in GREENFIELD_PHASES]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_no_duplicate_evolution_ids(self) -> None:
        ids = [p["id"] for p in EVOLUTION_PHASES]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


# ---------------------------------------------------------------------------
# render_backlog_summary (v3.11)
# ---------------------------------------------------------------------------


BACKLOG_EMPTY = """\
# Backlog

No CRs yet.
"""

BACKLOG_SINGLE_CR = """\
# Backlog

## CR-001: Fix login button

**Status:** new
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Created:** 2026-02-01
**Description:** Login button doesn't work on mobile
"""

BACKLOG_MULTI_CR = """\
# Backlog

## CR-001: Fix login button

**Status:** new
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Created:** 2026-02-01
**Description:** Login button doesn't work on mobile

## CR-002: Add dark mode

**Status:** triaged
**Priority:** medium
**Type:** enhancement
**Version Lane:** v1.1
**Created:** 2026-01-20
**Description:** Users want dark mode

## CR-003: Refactor auth module

**Status:** planned
**Priority:** low
**Type:** refactor
**Version Lane:** v1.2
**Created:** 2026-01-05
**Description:** Auth module needs cleanup

## CR-004: Fix crash on export

**Status:** resolved
**Priority:** critical
**Type:** bug
**Version Lane:** v1.1
**Created:** 2025-12-15
**Description:** App crashes when exporting large files

## CR-005: Update dependencies

**Status:** closed
**Priority:** low
**Type:** maintenance
**Version Lane:** v1.0
**Created:** 2025-11-01
**Description:** Bump all deps to latest

## CR-006: Add search feature

**Status:** in-progress
**Priority:** high
**Type:** feature
**Version Lane:** v1.2
**Created:** 2026-02-05
**Description:** Full-text search across documents

## CR-007: Remove legacy API

**Status:** wontfix
**Priority:** low
**Type:** cleanup
**Version Lane:** unassigned
**Created:** 2025-10-01
**Description:** Legacy API still has some users
"""

BACKLOG_NO_LANE = """\
# Backlog

## CR-001: Orphan CR

**Status:** new
**Priority:** high
**Type:** bug
**Created:** 2026-02-06
**Description:** No version lane specified
"""

BACKLOG_PROMOTED = """\
# Backlog

## CR-001: Promoted CR

**Status:** promoted → CR-005
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Created:** 2026-02-01
**Description:** Was a deferred finding, now promoted
"""


class TestRenderBacklogSummary:
    """Test render_backlog_summary with various backlog.md contents."""

    def test_missing_file(self, tmp_path: Path) -> None:
        result = render_backlog_summary(tmp_path / "nonexistent.md")
        assert "does not exist" in result

    def test_empty_backlog(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_EMPTY, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "empty" in result.lower() or "no CRs" in result.lower()

    def test_single_cr_status(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_SINGLE_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "new" in result
        assert "BACKLOG SUMMARY" in result

    def test_single_cr_version_lane(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_SINGLE_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "v1.1" in result

    def test_single_cr_aging(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_SINGLE_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "Aging" in result

    def test_multi_cr_all_statuses(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "new" in result
        assert "triaged" in result
        assert "planned" in result
        assert "resolved" in result
        assert "closed" in result
        assert "in-progress" in result
        assert "wontfix" in result

    def test_multi_cr_version_lanes(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "v1.0" in result
        assert "v1.1" in result
        assert "v1.2" in result
        assert "unassigned" in result

    def test_multi_cr_open_closed_counts(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        # v1.1 has: new (open), triaged (open), resolved (closed) = 2 open, 1 closed
        assert "v1.1" in result
        assert "open" in result
        assert "closed" in result

    def test_multi_cr_aging_buckets(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "< 7 days" in result
        assert "7-30 days" in result
        assert "> 30 days" in result

    def test_multi_cr_old_cr_warning(self, tmp_path: Path) -> None:
        """CRs older than 30 days should get a warning marker."""
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        # CR-003 is planned (open) with date 2026-01-05 — should be > 30 days
        assert "!!!" in result

    def test_no_version_lane_defaults_unassigned(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_NO_LANE, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "unassigned" in result

    def test_promoted_status(self, tmp_path: Path) -> None:
        """CRs with 'promoted → CR-NNN' status should be parsed correctly."""
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_PROMOTED, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "promoted" in result

    def test_output_has_section_headers(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "By status:" in result
        assert "By version lane:" in result

    def test_output_format_separators(self, tmp_path: Path) -> None:
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "===" in result

    def test_cr_without_date_defaults_recent(self, tmp_path: Path) -> None:
        """A CR with no Created field should be counted as < 7 days."""
        no_date = """\
# Backlog

## CR-001: No date CR

**Status:** new
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Description:** No created date
"""
        f = tmp_path / "backlog.md"
        f.write_text(no_date, encoding="utf-8")
        result = render_backlog_summary(f)
        # Should still show aging section since it's open
        assert "Aging" in result
        assert "< 7 days" in result

    def test_only_closed_crs_no_aging(self, tmp_path: Path) -> None:
        """If all CRs are closed, no aging section should appear."""
        all_closed = """\
# Backlog

## CR-001: Done thing

**Status:** closed
**Priority:** low
**Type:** bug
**Version Lane:** v1.0
**Created:** 2025-12-01
**Description:** Already fixed

## CR-002: Rejected thing

**Status:** wontfix
**Priority:** low
**Type:** cleanup
**Version Lane:** v1.0
**Created:** 2025-11-01
**Description:** Not worth fixing
"""
        f = tmp_path / "backlog.md"
        f.write_text(all_closed, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "Aging" not in result

    def test_duplicate_and_superseded_statuses(self, tmp_path: Path) -> None:
        """Verify duplicate and superseded are recognized as closed statuses."""
        backlog = """\
# Backlog

## CR-001: Duplicate issue

**Status:** duplicate
**Priority:** low
**Type:** bug
**Version Lane:** v1.1
**Created:** 2026-01-15
**Description:** Duplicate of CR-002

## CR-002: Superseded feature

**Status:** superseded
**Priority:** medium
**Type:** feature
**Version Lane:** v1.2
**Created:** 2026-01-10
**Description:** Replaced by CR-003
"""
        f = tmp_path / "backlog.md"
        f.write_text(backlog, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "duplicate" in result
        assert "superseded" in result
        # Both are closed statuses, so no aging section
        assert "Aging" not in result


# ---------------------------------------------------------------------------
# Evolution Pipeline Lifecycle (v3.11)
# ---------------------------------------------------------------------------


class TestEvolutionPipelineLifecycle:
    """Test the full evolution pipeline including new v3.11 phases."""

    def test_evolution_init_has_all_phases(self, status_file: Path) -> None:
        data = init_pipeline("evolution", "Evo Project", path=status_file)
        ids = [p["id"] for p in data["phases"]]
        assert "intake" in ids
        assert "plan-delta" in ids
        assert "synthesize" in ids
        assert "execute" in ids
        assert "runtime-qa" in ids
        assert "qa-fix-pass" in ids
        assert "release" in ids
        assert "retro" in ids

    def test_evolution_phase_count(self, status_file: Path) -> None:
        data = init_pipeline("evolution", "Evo Project", path=status_file)
        assert len(data["phases"]) == 8

    def test_greenfield_phase_count(self, status_file: Path) -> None:
        data = init_pipeline("greenfield", "GF Project", path=status_file)
        assert len(data["phases"]) == 9  # includes specialists/competition + plan-define

    def test_evolution_can_start_release(self, status_file: Path) -> None:
        """Release phase can be started in evolution pipeline."""
        init_pipeline("evolution", "Test", path=status_file)
        # Complete all prior phases
        for phase_id in ["intake", "plan-delta", "synthesize", "execute", "runtime-qa", "qa-fix-pass"]:
            start_phase(phase_id, path=status_file)
            complete_phase(phase_id, path=status_file)
        # Now start release
        start_phase("release", path=status_file)
        data = load_pipeline(status_file)
        assert data["current_phase"] == "release"

    def test_evolution_release_to_retro(self, status_file: Path) -> None:
        """Can complete release and start retro."""
        init_pipeline("evolution", "Test", path=status_file)
        for phase_id in ["intake", "plan-delta", "synthesize", "execute", "runtime-qa", "qa-fix-pass"]:
            start_phase(phase_id, path=status_file)
            complete_phase(phase_id, path=status_file)
        start_phase("release", path=status_file)
        complete_phase("release", summary="v1.1 released", path=status_file)
        start_phase("retro", path=status_file)
        data = load_pipeline(status_file)
        assert data["current_phase"] == "retro"

    def test_evolution_skip_qa_phases(self, status_file: Path) -> None:
        """Runtime QA and QA fix pass can be skipped."""
        init_pipeline("evolution", "Test", path=status_file)
        for phase_id in ["intake", "plan-delta", "synthesize", "execute"]:
            start_phase(phase_id, path=status_file)
            complete_phase(phase_id, path=status_file)
        skip_phase("runtime-qa", reason="no frontend changes", path=status_file)
        skip_phase("qa-fix-pass", reason="no QA needed", path=status_file)
        start_phase("release", path=status_file)
        data = load_pipeline(status_file)
        qa = next(p for p in data["phases"] if p["id"] == "runtime-qa")
        assert qa["status"] == "skipped"
        fix = next(p for p in data["phases"] if p["id"] == "qa-fix-pass")
        assert fix["status"] == "skipped"

    def test_evolution_skip_release(self, status_file: Path) -> None:
        """Release phase can be skipped (e.g., for quick fixes)."""
        init_pipeline("evolution", "Test", path=status_file)
        for phase_id in ["intake", "plan-delta", "synthesize", "execute"]:
            start_phase(phase_id, path=status_file)
            complete_phase(phase_id, path=status_file)
        skip_phase("runtime-qa", path=status_file)
        skip_phase("qa-fix-pass", path=status_file)
        skip_phase("release", reason="quick fix, no formal release", path=status_file)
        start_phase("retro", path=status_file)
        data = load_pipeline(status_file)
        rel = next(p for p in data["phases"] if p["id"] == "release")
        assert rel["status"] == "skipped"

    def test_evolution_add_specialist_between_delta_and_synthesize(self, status_file: Path) -> None:
        """Specialists can be dynamically inserted in evolution pipeline."""
        init_pipeline("evolution", "Test", path=status_file)
        add_phase("specialists/backend", "Backend Deep Dive", "plan-delta", path=status_file)
        data = load_pipeline(status_file)
        ids = [p["id"] for p in data["phases"]]
        # Backend should be between plan-delta and synthesize
        assert ids.index("specialists/backend") > ids.index("plan-delta")
        assert ids.index("specialists/backend") < ids.index("synthesize")

    def test_greenfield_release_in_dashboard(self, status_file: Path) -> None:
        """Release phase appears in greenfield dashboard output."""
        init_pipeline("greenfield", "Dashboard Test", path=status_file)
        output = render_dashboard(status_file)
        assert "/release" in output

    def test_evolution_release_in_dashboard(self, status_file: Path) -> None:
        """Release phase appears in evolution dashboard output."""
        init_pipeline("evolution", "Dashboard Test", path=status_file)
        output = render_dashboard(status_file)
        assert "/release" in output

    def test_evolution_full_lifecycle_dashboard(self, status_file: Path) -> None:
        """Dashboard reflects the full evolution lifecycle."""
        init_pipeline("evolution", "Full Cycle", path=status_file)
        for phase_id in [
            "intake", "plan-delta", "synthesize", "execute",
            "runtime-qa", "qa-fix-pass", "release", "retro",
        ]:
            start_phase(phase_id, path=status_file)
            complete_phase(phase_id, path=status_file)
        output = render_dashboard(status_file)
        assert "8/8 phases complete" in output


# ---------------------------------------------------------------------------
# CLI backlog-summary integration (v3.11)
# ---------------------------------------------------------------------------


class TestBacklogSummaryCLI:
    """Test the backlog-summary CLI subcommand end-to-end."""

    def test_cli_backlog_summary_no_file(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        """Running backlog-summary with nonexistent file gives a graceful message."""
        from pipeline_tracker import main as pt_main

        sys_argv_backup = sys.argv
        try:
            sys.argv = [
                "pipeline_tracker.py",
                "backlog-summary",
                "--backlog-file", str(tmp_path / "missing.md"),
            ]
            pt_main()
        finally:
            sys.argv = sys_argv_backup
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_cli_backlog_summary_with_data(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        """Running backlog-summary with a populated backlog renders output."""
        from pipeline_tracker import main as pt_main

        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")

        sys_argv_backup = sys.argv
        try:
            sys.argv = [
                "pipeline_tracker.py",
                "backlog-summary",
                "--backlog-file", str(f),
            ]
            pt_main()
        finally:
            sys.argv = sys_argv_backup
        captured = capsys.readouterr()
        assert "BACKLOG SUMMARY" in captured.out
        assert "By status:" in captured.out

    def test_cli_backlog_summary_empty(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        """Running backlog-summary with empty backlog gives a clean message."""
        from pipeline_tracker import main as pt_main

        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_EMPTY, encoding="utf-8")

        sys_argv_backup = sys.argv
        try:
            sys.argv = [
                "pipeline_tracker.py",
                "backlog-summary",
                "--backlog-file", str(f),
            ]
            pt_main()
        finally:
            sys.argv = sys_argv_backup
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower() or "no CRs" in captured.out.lower()


# ---------------------------------------------------------------------------
# Edge Cases (v3.11)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and regression tests for v3.11 features."""

    def test_backlog_with_malformed_cr(self, tmp_path: Path) -> None:
        """Backlog with CRs missing fields should not crash."""
        malformed = """\
# Backlog

## CR-001: Missing fields

Some random text but no structured fields.

## CR-002: Only status

**Status:** new
"""
        f = tmp_path / "backlog.md"
        f.write_text(malformed, encoding="utf-8")
        result = render_backlog_summary(f)
        # Should not crash, should count what it can
        assert "BACKLOG SUMMARY" in result

    def test_backlog_with_unicode(self, tmp_path: Path) -> None:
        """Backlog with unicode characters should be handled."""
        unicode_backlog = """\
# Backlog

## CR-001: Fixer le bouton d'authentification

**Status:** new
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Created:** 2026-02-01
**Description:** Le bouton ne marche pas sur mobile — c'est un probl\u00e8me
"""
        f = tmp_path / "backlog.md"
        f.write_text(unicode_backlog, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "BACKLOG SUMMARY" in result
        assert "new" in result

    def test_backlog_with_many_crs(self, tmp_path: Path) -> None:
        """Backlog with many CRs should work correctly."""
        lines = ["# Backlog\n"]
        for i in range(1, 51):
            status = ["new", "triaged", "planned", "in-progress", "resolved", "closed"][i % 6]
            lane = f"v1.{i % 3}"
            lines.append(f"\n## CR-{i:03d}: Issue {i}\n")
            lines.append(f"**Status:** {status}\n")
            lines.append(f"**Version Lane:** {lane}\n")
            lines.append(f"**Created:** 2026-01-{(i % 28) + 1:02d}\n")
        f = tmp_path / "backlog.md"
        f.write_text("\n".join(lines), encoding="utf-8")
        result = render_backlog_summary(f)
        assert "BACKLOG SUMMARY" in result
        # Should have all version lanes
        assert "v1.0" in result
        assert "v1.1" in result
        assert "v1.2" in result

    def test_greenfield_init_preserves_release_phase(self, status_file: Path) -> None:
        """After init, the release phase exists and is pending."""
        data = init_pipeline("greenfield", "Test", path=status_file)
        release = next(p for p in data["phases"] if p["id"] == "release")
        assert release["status"] == "pending"
        assert release["label"] == "Release Closure"
        assert release["command"] == "/release"

    def test_evolution_init_preserves_release_phase(self, status_file: Path) -> None:
        """After init, the release phase exists and is pending."""
        data = init_pipeline("evolution", "Test", path=status_file)
        release = next(p for p in data["phases"] if p["id"] == "release")
        assert release["status"] == "pending"
        assert release["label"] == "Release Closure"
        assert release["command"] == "/release"

    def test_backlog_summary_with_invalid_date(self, tmp_path: Path) -> None:
        """CR with invalid date format should not crash."""
        bad_date = """\
# Backlog

## CR-001: Bad date

**Status:** new
**Priority:** high
**Type:** bug
**Version Lane:** v1.1
**Created:** not-a-date
**Description:** Invalid date format
"""
        f = tmp_path / "backlog.md"
        f.write_text(bad_date, encoding="utf-8")
        result = render_backlog_summary(f)
        assert "BACKLOG SUMMARY" in result
        # Should not crash — bad date defaults to < 7 days

    def test_backlog_summary_status_order(self, tmp_path: Path) -> None:
        """Statuses should appear in the canonical order."""
        f = tmp_path / "backlog.md"
        f.write_text(BACKLOG_MULTI_CR, encoding="utf-8")
        result = render_backlog_summary(f)
        lines = result.split("\n")
        # Find status lines
        status_lines = []
        in_status_section = False
        for line in lines:
            if "By status:" in line:
                in_status_section = True
                continue
            if in_status_section:
                if line.strip() == "" or "By version" in line:
                    break
                status_lines.append(line.strip().split()[0])
        # new should come before triaged, triaged before planned, etc.
        expected_order = [
            "new", "triaged", "planned", "in-progress",
            "resolved", "closed", "wontfix",
        ]
        # Filter to only statuses that appear
        present = [s for s in expected_order if s in status_lines]
        assert present == [s for s in status_lines if s in expected_order]
