"""Tests for .claude/tools/chain_manager.py — state chain audit trail management."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from chain_manager import (
    CHAIN_FILE,
    EMPTY_CHAIN,
    build_parser,
    get_summary,
    hash_content,
    main,
    record_entry,
    verify_integrity,
)


@pytest.fixture
def chain_file(tmp_path: Path) -> Path:
    """Return a temporary chain file path (does not exist yet)."""
    return tmp_path / "state-chain" / "chain.json"


@pytest.fixture
def input_file(tmp_path: Path) -> Path:
    """Create a temporary input file with test content."""
    f = tmp_path / "input.txt"
    f.write_text("test input data", encoding="utf-8")
    return f


@pytest.fixture
def output_file(tmp_path: Path) -> Path:
    """Create a temporary output file with test content."""
    f = tmp_path / "output.txt"
    f.write_text("test output data", encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# TestHashContent
# ---------------------------------------------------------------------------


class TestHashContent:
    """Test hash_content function for SHA-256 hashing."""

    def test_determinism_same_input(self) -> None:
        """Same input produces the same hash every time."""
        hash1 = hash_content("test content")
        hash2 = hash_content("test content")
        assert hash1 == hash2

    def test_different_inputs_different_hashes(self) -> None:
        """Different inputs produce different hashes."""
        hash1 = hash_content("content A")
        hash2 = hash_content("content B")
        assert hash1 != hash2

    def test_prefix_format(self) -> None:
        """Hash output has sha256: prefix."""
        result = hash_content("sample text")
        assert result.startswith("sha256:")

    def test_empty_string(self) -> None:
        """Empty string can be hashed."""
        result = hash_content("")
        assert result.startswith("sha256:")
        assert len(result) > 7  # sha256: + hex digest

    def test_unicode_handling(self) -> None:
        """Unicode characters are correctly hashed."""
        result1 = hash_content("Hello 世界")
        result2 = hash_content("Hello 世界")
        assert result1 == result2
        assert result1.startswith("sha256:")


# ---------------------------------------------------------------------------
# TestLoadSaveChain
# ---------------------------------------------------------------------------


class TestLoadSaveChain:
    """Test internal _load_chain and _save_chain functions."""

    def test_missing_file_returns_empty_chain(self, chain_file: Path) -> None:
        """Loading a nonexistent file returns EMPTY_CHAIN structure."""
        from chain_manager import _load_chain

        data = _load_chain(chain_file)
        assert data["_schema"]["version"] == "1.0"
        assert data["entries"] == []
        assert data["integrity"]["chain_valid"] is True

    def test_existing_file_loads_correctly(self, chain_file: Path) -> None:
        """Loading an existing chain file returns its contents."""
        from chain_manager import _load_chain, _save_chain

        test_data = {
            "_schema": {"version": "1.0", "description": "Test chain"},
            "entries": [{"seq": 1, "task_id": "T01"}],
            "integrity": {"last_verified": None, "chain_valid": True, "broken_links": []},
        }
        _save_chain(chain_file, test_data)
        loaded = _load_chain(chain_file)
        assert loaded["entries"][0]["task_id"] == "T01"

    def test_save_creates_parent_directories(self, chain_file: Path) -> None:
        """Saving creates parent directories if they don't exist."""
        from chain_manager import _save_chain

        assert not chain_file.parent.exists()
        test_data = json.loads(json.dumps(EMPTY_CHAIN))
        _save_chain(chain_file, test_data)
        assert chain_file.parent.exists()
        assert chain_file.exists()

    def test_round_trip(self, chain_file: Path) -> None:
        """Save then load returns the same data."""
        from chain_manager import _load_chain, _save_chain

        test_data = {
            "_schema": {"version": "1.0", "description": "Round trip test"},
            "entries": [
                {"seq": 1, "task_id": "T01", "stage": "implement"},
                {"seq": 2, "task_id": "T02", "stage": "review"},
            ],
            "integrity": {"last_verified": None, "chain_valid": True, "broken_links": []},
        }
        _save_chain(chain_file, test_data)
        loaded = _load_chain(chain_file)
        assert loaded["_schema"]["description"] == "Round trip test"
        assert len(loaded["entries"]) == 2
        assert loaded["entries"][1]["task_id"] == "T02"

    def test_empty_chain_structure(self) -> None:
        """EMPTY_CHAIN constant has the expected structure."""
        assert "_schema" in EMPTY_CHAIN
        assert "version" in EMPTY_CHAIN["_schema"]
        assert "entries" in EMPTY_CHAIN
        assert "integrity" in EMPTY_CHAIN
        assert isinstance(EMPTY_CHAIN["entries"], list)
        assert EMPTY_CHAIN["integrity"]["chain_valid"] is True


# ---------------------------------------------------------------------------
# TestRecordEntry
# ---------------------------------------------------------------------------


class TestRecordEntry:
    """Test record_entry function for creating chain entries."""
    def test_first_entry_has_null_prev_hash(self, chain_file: Path) -> None:
        """First entry in chain has prev_hash=None."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="first input",
            output_data="first output",
            description="First entry",
            chain_path=chain_file,
        )
        assert entry["prev_hash"] is None

    def test_second_entry_links_to_first(self, chain_file: Path) -> None:
        """Second entry's prev_hash links to first entry's output_hash."""
        entry1 = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="first input",
            output_data="first output",
            description="First entry",
            chain_path=chain_file,
        )
        entry2 = record_entry(
            task_id="T02",
            stage="review",
            agent="code-reviewer",
            input_data="second input",
            output_data="second output",
            description="Second entry",
            chain_path=chain_file,
        )
        assert entry2["prev_hash"] == entry1["output_hash"]

    def test_seq_increments(self, chain_file: Path) -> None:
        """Sequence numbers increment with each entry."""
        entry1 = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input 1",
            output_data="output 1",
            description="Entry 1",
            chain_path=chain_file,
        )
        entry2 = record_entry(
            task_id="T02",
            stage="review",
            agent="code-reviewer",
            input_data="input 2",
            output_data="output 2",
            description="Entry 2",
            chain_path=chain_file,
        )
        assert entry1["seq"] == 1
        assert entry2["seq"] == 2

    def test_all_fields_present(self, chain_file: Path) -> None:
        """Entry contains all required fields."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Test entry",
            pipeline="greenfield",
            verdict="PASS",
            warnings=["W1", "W2"],
            metadata={"key": "value"},
            chain_path=chain_file,
        )
        assert entry["seq"] == 1
        assert entry["task_id"] == "T01"
        assert entry["stage"] == "implement"
        assert entry["agent"] == "executor"
        assert entry["pipeline"] == "greenfield"
        assert entry["verdict"] == "PASS"
        assert entry["warnings"] == ["W1", "W2"]
        assert entry["metadata"]["key"] == "value"
        assert "timestamp" in entry
        assert "input_hash" in entry
        assert "output_hash" in entry
        assert "prev_hash" in entry
        assert "description" in entry

    def test_verdict_optional(self, chain_file: Path) -> None:
        """Verdict can be None."""
        entry = record_entry(
            task_id="T01",
            stage="plan",
            agent="planner",
            input_data="input",
            output_data="output",
            description="Planning entry",
            chain_path=chain_file,
        )
        assert entry["verdict"] is None

    def test_warnings_default_to_empty_list(self, chain_file: Path) -> None:
        """Warnings default to empty list when not provided."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry without warnings",
            chain_path=chain_file,
        )
        assert entry["warnings"] == []

    def test_metadata_default_to_empty_dict(self, chain_file: Path) -> None:
        """Metadata defaults to empty dict when not provided."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry without metadata",
            chain_path=chain_file,
        )
        assert entry["metadata"] == {}

    def test_custom_verdict_warnings_metadata(self, chain_file: Path) -> None:
        """Custom verdict, warnings, and metadata are correctly stored."""
        entry = record_entry(
            task_id="T05",
            stage="review",
            agent="code-reviewer",
            input_data="review input",
            output_data="review output",
            description="Code review",
            verdict="FAIL",
            warnings=["Line too long", "Missing type hint"],
            metadata={"review_cycles": 2, "severity": "high"},
            chain_path=chain_file,
        )
        assert entry["verdict"] == "FAIL"
        assert len(entry["warnings"]) == 2
        assert "Line too long" in entry["warnings"]
        assert entry["metadata"]["review_cycles"] == 2

    def test_pipeline_field(self, chain_file: Path) -> None:
        """Pipeline field is correctly stored."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Test entry",
            pipeline="evolution",
            chain_path=chain_file,
        )
        assert entry["pipeline"] == "evolution"

    def test_file_persistence(self, chain_file: Path) -> None:
        """Entry survives reload from file."""
        from chain_manager import _load_chain

        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Persistent entry",
            chain_path=chain_file,
        )
        loaded = _load_chain(chain_file)
        assert len(loaded["entries"]) == 1
        assert loaded["entries"][0]["task_id"] == "T01"

    def test_timestamp_format(self, chain_file: Path) -> None:
        """Timestamp is ISO 8601 format with milliseconds."""
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Timestamp test",
            chain_path=chain_file,
        )
        # Should be parseable as ISO format
        ts = entry["timestamp"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo == timezone.utc

    def test_input_output_hashes_deterministic(self, chain_file: Path) -> None:
        """Input and output hashes are deterministic."""
        entry1 = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="same input",
            output_data="same output",
            description="Entry 1",
            chain_path=chain_file,
        )
        entry2 = record_entry(
            task_id="T02",
            stage="review",
            agent="code-reviewer",
            input_data="same input",
            output_data="same output",
            description="Entry 2",
            chain_path=chain_file,
        )
        assert entry1["input_hash"] == entry2["input_hash"]
        assert entry1["output_hash"] == entry2["output_hash"]


# ---------------------------------------------------------------------------
# TestVerifyIntegrity
# ---------------------------------------------------------------------------


class TestVerifyIntegrity:
    """Test verify_integrity function for chain validation."""
    def test_empty_chain_is_valid(self, chain_file: Path) -> None:
        """Empty chain is considered valid."""
        from chain_manager import _save_chain

        _save_chain(chain_file, json.loads(json.dumps(EMPTY_CHAIN)))
        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is True
        assert broken == []

    def test_single_entry_valid(self, chain_file: Path) -> None:
        """Single entry chain is valid."""
        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Single entry",
            chain_path=chain_file,
        )
        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is True
        assert broken == []

    def test_multi_entry_valid_chain(self, chain_file: Path) -> None:
        """Multi-entry chain with correct links is valid."""
        for i in range(5):
            record_entry(
                task_id=f"T{i:02d}",
                stage="implement",
                agent="executor",
                input_data=f"input {i}",
                output_data=f"output {i}",
                description=f"Entry {i}",
                chain_path=chain_file,
            )
        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is True
        assert broken == []

    def test_broken_first_entry(self, chain_file: Path) -> None:
        """First entry with non-null prev_hash is invalid."""
        from chain_manager import _load_chain, _save_chain

        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry",
            chain_path=chain_file,
        )
        # Manually corrupt the chain
        data = _load_chain(chain_file)
        data["entries"][0]["prev_hash"] = "sha256:fake"
        _save_chain(chain_file, data)

        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is False
        assert len(broken) == 1
        assert "Entry 1" in broken[0]

    def test_broken_middle_link(self, chain_file: Path) -> None:
        """Broken link in the middle of chain is detected."""
        from chain_manager import _load_chain, _save_chain

        for i in range(3):
            record_entry(
                task_id=f"T{i:02d}",
                stage="implement",
                agent="executor",
                input_data=f"input {i}",
                output_data=f"output {i}",
                description=f"Entry {i}",
                chain_path=chain_file,
            )
        # Corrupt middle entry
        data = _load_chain(chain_file)
        data["entries"][1]["prev_hash"] = "sha256:wronghash"
        _save_chain(chain_file, data)

        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is False
        assert len(broken) == 1
        assert "Entry 2" in broken[0]

    def test_integrity_section_updated(self, chain_file: Path) -> None:
        """Integrity section is updated after verify."""
        from chain_manager import _load_chain

        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry",
            chain_path=chain_file,
        )
        verify_integrity(chain_path=chain_file)
        data = _load_chain(chain_file)
        assert data["integrity"]["last_verified"] is not None
        assert data["integrity"]["chain_valid"] is True

    def test_last_verified_timestamp_set(self, chain_file: Path) -> None:
        """last_verified is set to current timestamp."""
        from chain_manager import _load_chain

        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry",
            chain_path=chain_file,
        )
        verify_integrity(chain_path=chain_file)
        data = _load_chain(chain_file)
        ts = data["integrity"]["last_verified"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo == timezone.utc

    def test_chain_valid_reflects_result(self, chain_file: Path) -> None:
        """chain_valid field reflects verification result."""
        from chain_manager import _load_chain, _save_chain

        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Entry",
            chain_path=chain_file,
        )
        # First verify valid chain
        verify_integrity(chain_path=chain_file)
        data = _load_chain(chain_file)
        assert data["integrity"]["chain_valid"] is True

        # Corrupt it
        data["entries"][0]["prev_hash"] = "sha256:fake"
        _save_chain(chain_file, data)
        verify_integrity(chain_path=chain_file)
        data = _load_chain(chain_file)
        assert data["integrity"]["chain_valid"] is False


# ---------------------------------------------------------------------------
# TestGetSummary
# ---------------------------------------------------------------------------


class TestGetSummary:
    """Test get_summary function for generating chain summaries."""
    def test_empty_chain_message(self, chain_file: Path) -> None:
        """Empty chain returns appropriate message."""
        from chain_manager import _save_chain

        _save_chain(chain_file, json.loads(json.dumps(EMPTY_CHAIN)))
        summary = get_summary(chain_path=chain_file)
        assert "empty" in summary.lower()

    def test_single_entry_output(self, chain_file: Path) -> None:
        """Single entry produces formatted output."""
        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="First task",
            pipeline="greenfield",
            chain_path=chain_file,
        )
        summary = get_summary(chain_path=chain_file)
        assert "T01" in summary
        assert "implement" in summary
        assert "executor" in summary
        assert "First task" in summary

    def test_multi_entry_output(self, chain_file: Path) -> None:
        """Multiple entries are all included in output."""
        for i in range(3):
            record_entry(
                task_id=f"T{i:02d}",
                stage="implement",
                agent="executor",
                input_data=f"input {i}",
                output_data=f"output {i}",
                description=f"Task {i}",
                chain_path=chain_file,
            )
        summary = get_summary(chain_path=chain_file)
        assert "T00" in summary
        assert "T01" in summary
        assert "T02" in summary
        assert "3" in summary  # entry count

    def test_task_id_filter(self, chain_file: Path) -> None:
        """Filtering by task_id returns only matching entries."""
        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input 1",
            output_data="output 1",
            description="Task 1",
            chain_path=chain_file,
        )
        record_entry(
            task_id="T02",
            stage="implement",
            agent="executor",
            input_data="input 2",
            output_data="output 2",
            description="Task 2",
            chain_path=chain_file,
        )
        summary = get_summary(task_id="T01", chain_path=chain_file)
        assert "T01" in summary
        assert "T02" not in summary

    def test_task_id_filter_no_match(self, chain_file: Path) -> None:
        """Filtering with no matches returns appropriate message."""
        record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="Task",
            chain_path=chain_file,
        )
        summary = get_summary(task_id="T99", chain_path=chain_file)
        assert "No chain entries for task T99" in summary

    def test_verdict_and_warnings_in_output(self, chain_file: Path) -> None:
        """Verdict and warnings appear in summary output."""
        record_entry(
            task_id="T01",
            stage="review",
            agent="code-reviewer",
            input_data="input",
            output_data="output",
            description="Code review",
            verdict="FAIL",
            warnings=["Missing docstring", "Type hint needed"],
            chain_path=chain_file,
        )
        summary = get_summary(chain_path=chain_file)
        assert "FAIL" in summary
        assert "Missing docstring" in summary
        assert "Type hint needed" in summary


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    """Test CLI argument parsing and end-to-end main() execution."""
    def test_build_parser_record_subcommand(self) -> None:
        """Parser accepts record subcommand with required arguments."""
        parser = build_parser()
        args = parser.parse_args([
            "record",
            "--task", "T01",
            "--stage", "implement",
            "--agent", "executor",
            "--input-file", "in.txt",
            "--output-file", "out.txt",
            "--description", "Test entry",
        ])
        assert args.command == "record"
        assert args.task == "T01"
        assert args.stage == "implement"
        assert args.agent == "executor"

    def test_build_parser_verify_subcommand(self) -> None:
        """Parser accepts verify subcommand."""
        parser = build_parser()
        args = parser.parse_args(["verify"])
        assert args.command == "verify"

    def test_build_parser_summary_subcommand(self) -> None:
        """Parser accepts summary subcommand with optional task filter."""
        parser = build_parser()
        args = parser.parse_args(["summary", "--task", "T05"])
        assert args.command == "summary"
        assert args.task == "T05"

    def test_chain_file_override(self) -> None:
        """--chain-file overrides default chain file path."""
        parser = build_parser()
        args = parser.parse_args([
            "--chain-file", "/tmp/custom-chain.json",
            "verify",
        ])
        assert args.chain_file == "/tmp/custom-chain.json"

    def test_end_to_end_record_via_main(
        self,
        chain_file: Path,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """End-to-end record command via main()."""
        exit_code = main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "implement",
            "--agent", "executor",
            "--input-file", str(input_file),
            "--output-file", str(output_file),
            "--description", "End-to-end test",
            "--pipeline", "greenfield",
            "--verdict", "PASS",
        ])
        assert exit_code == 0
        assert chain_file.exists()

    def test_end_to_end_verify_via_main(
        self,
        chain_file: Path,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """End-to-end verify command via main()."""
        # Record an entry first
        main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "implement",
            "--agent", "executor",
            "--input-file", str(input_file),
            "--output-file", str(output_file),
            "--description", "Test entry",
        ])
        # Verify it
        exit_code = main([
            "--chain-file", str(chain_file),
            "verify",
        ])
        assert exit_code == 0

    def test_end_to_end_summary_via_main(
        self,
        chain_file: Path,
        input_file: Path,
        output_file: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """End-to-end summary command via main()."""
        # Record an entry first
        main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "implement",
            "--agent", "executor",
            "--input-file", str(input_file),
            "--output-file", str(output_file),
            "--description", "Test entry",
        ])
        # Get summary
        exit_code = main([
            "--chain-file", str(chain_file),
            "summary",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "T01" in captured.out

    def test_verify_returns_1_on_broken_chain(
        self,
        chain_file: Path,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """Verify returns exit code 1 when chain is broken."""
        from chain_manager import _load_chain, _save_chain

        # Record an entry
        main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "implement",
            "--agent", "executor",
            "--input-file", str(input_file),
            "--output-file", str(output_file),
            "--description", "Test entry",
        ])
        # Corrupt the chain
        data = _load_chain(chain_file)
        data["entries"][0]["prev_hash"] = "sha256:corrupt"
        _save_chain(chain_file, data)

        # Verify should return 1
        exit_code = main([
            "--chain-file", str(chain_file),
            "verify",
        ])
        assert exit_code == 1

    def test_record_with_metadata_json(
        self,
        chain_file: Path,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """Record command accepts metadata as JSON string."""
        from chain_manager import _load_chain

        exit_code = main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "review",
            "--agent", "code-reviewer",
            "--input-file", str(input_file),
            "--output-file", str(output_file),
            "--description", "Review with metadata",
            "--metadata", '{"review_cycles": 3, "severity": "high"}',
        ])
        assert exit_code == 0
        data = _load_chain(chain_file)
        assert data["entries"][0]["metadata"]["review_cycles"] == 3
        assert data["entries"][0]["metadata"]["severity"] == "high"


# ---------------------------------------------------------------------------
# v3.15: Corrupted JSON recovery
# ---------------------------------------------------------------------------


class TestCorruptedJsonRecovery:
    """Test _load_chain handles corrupted JSON files."""

    def test_corrupted_file_returns_empty_chain(self, chain_file: Path) -> None:
        """Corrupted JSON returns a fresh empty chain."""
        from chain_manager import _load_chain

        chain_file.parent.mkdir(parents=True, exist_ok=True)
        chain_file.write_text("{invalid json!!!", encoding="utf-8")
        data = _load_chain(chain_file)
        assert data["entries"] == []
        assert data["_schema"]["version"] == "1.0"

    def test_corrupted_file_creates_backup(self, chain_file: Path) -> None:
        """Corrupted JSON file is renamed to .bak."""
        from chain_manager import _load_chain

        chain_file.parent.mkdir(parents=True, exist_ok=True)
        chain_file.write_text("{bad", encoding="utf-8")
        backup = chain_file.with_suffix(".json.bak")
        _load_chain(chain_file)
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "{bad"

    def test_corrupted_file_original_removed(self, chain_file: Path) -> None:
        """Original corrupted file is renamed (no longer at original path)."""
        from chain_manager import _load_chain

        chain_file.parent.mkdir(parents=True, exist_ok=True)
        chain_file.write_text("not json", encoding="utf-8")
        _load_chain(chain_file)
        # Original file was renamed to .bak, so it should not exist
        assert not chain_file.exists()

    def test_record_after_corruption_creates_new_chain(self, chain_file: Path) -> None:
        """Recording after corruption starts a fresh chain."""
        chain_file.parent.mkdir(parents=True, exist_ok=True)
        chain_file.write_text("{corrupt!", encoding="utf-8")
        entry = record_entry(
            task_id="T01",
            stage="implement",
            agent="executor",
            input_data="input",
            output_data="output",
            description="After corruption",
            chain_path=chain_file,
        )
        assert entry["seq"] == 1
        assert entry["prev_hash"] is None


# ---------------------------------------------------------------------------
# v3.15: Atomic writes
# ---------------------------------------------------------------------------


class TestAtomicWrites:
    """Test _save_chain uses atomic write pattern."""

    def test_no_tmp_file_remains_after_save(self, chain_file: Path) -> None:
        """Atomic write cleans up .tmp file after successful save."""
        from chain_manager import _save_chain

        test_data = json.loads(json.dumps(EMPTY_CHAIN))
        _save_chain(chain_file, test_data)
        tmp_file = chain_file.with_suffix(".json.tmp")
        assert not tmp_file.exists()
        assert chain_file.exists()

    def test_saved_data_is_valid_json(self, chain_file: Path) -> None:
        """Atomically saved file contains valid JSON."""
        from chain_manager import _save_chain

        test_data = json.loads(json.dumps(EMPTY_CHAIN))
        test_data["entries"].append({"seq": 1, "task_id": "T01"})
        _save_chain(chain_file, test_data)
        loaded = json.loads(chain_file.read_text(encoding="utf-8"))
        assert loaded["entries"][0]["task_id"] == "T01"

    def test_file_ends_with_newline(self, chain_file: Path) -> None:
        """Atomic write produces file ending with newline."""
        from chain_manager import _save_chain

        _save_chain(chain_file, json.loads(json.dumps(EMPTY_CHAIN)))
        content = chain_file.read_text(encoding="utf-8")
        assert content.endswith("\n")
