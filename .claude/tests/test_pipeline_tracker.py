"""Tests for .claude/tools/pipeline_tracker.py — pipeline progress tracker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline_tracker import (
    add_phase,
    complete_phase,
    get_current,
    init_pipeline,
    load_pipeline,
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
