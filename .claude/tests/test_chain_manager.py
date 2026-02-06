"""Tests for .claude/tools/chain_manager.py — state chain audit trail."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chain_manager import (
    get_summary,
    hash_content,
    main,
    record_entry,
    verify_integrity,
)


@pytest.fixture()
def chain_file(tmp_path: Path) -> Path:
    """Return a temporary chain file path (does not exist yet)."""
    return tmp_path / "state-chain" / "chain.json"


# ---------------------------------------------------------------------------
# hash_content
# ---------------------------------------------------------------------------


class TestHashContent:
    def test_consistent_hash(self) -> None:
        """Same input always produces the same hash."""
        assert hash_content("hello") == hash_content("hello")

    def test_different_inputs_different_hashes(self) -> None:
        assert hash_content("hello") != hash_content("world")

    def test_sha256_prefix(self) -> None:
        result = hash_content("test")
        assert result.startswith("sha256:")

    def test_hex_length(self) -> None:
        result = hash_content("test")
        # "sha256:" (7 chars) + 64 hex chars = 71 total
        assert len(result) == 71

    def test_empty_string(self) -> None:
        result = hash_content("")
        assert result.startswith("sha256:")
        assert len(result) == 71

    def test_unicode_content(self) -> None:
        """Non-ASCII content hashes without error."""
        result = hash_content("données financières € £ ¥")
        assert result.startswith("sha256:")


# ---------------------------------------------------------------------------
# record_entry
# ---------------------------------------------------------------------------


class TestRecordEntry:
    def test_first_entry_has_null_prev_hash(self, chain_file: Path) -> None:
        entry = record_entry(
            task_id="T01",
            stage="verify",
            agent="self",
            input_data="input",
            output_data="output",
            description="First entry",
            chain_path=chain_file,
        )
        assert entry["prev_hash"] is None
        assert entry["seq"] == 1

    def test_chain_linking(self, chain_file: Path) -> None:
        """Second entry's prev_hash matches first entry's output_hash."""
        e1 = record_entry(
            task_id="T01",
            stage="verify",
            agent="self",
            input_data="input1",
            output_data="output1",
            description="Entry 1",
            chain_path=chain_file,
        )
        e2 = record_entry(
            task_id="T01",
            stage="review",
            agent="code-reviewer",
            input_data="input2",
            output_data="output2",
            description="Entry 2",
            chain_path=chain_file,
        )
        assert e2["prev_hash"] == e1["output_hash"]
        assert e2["seq"] == 2

    def test_three_entry_chain(self, chain_file: Path) -> None:
        """Three entries chain correctly."""
        e1 = record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="1",
            chain_path=chain_file,
        )
        e2 = record_entry(
            task_id="T01", stage="review", agent="code-reviewer",
            input_data="c", output_data="d", description="2",
            chain_path=chain_file,
        )
        e3 = record_entry(
            task_id="T01", stage="review", agent="security-auditor",
            input_data="e", output_data="f", description="3",
            chain_path=chain_file,
        )
        assert e1["prev_hash"] is None
        assert e2["prev_hash"] == e1["output_hash"]
        assert e3["prev_hash"] == e2["output_hash"]

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "chain.json"
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="in", output_data="out", description="test",
            chain_path=deep_path,
        )
        assert deep_path.exists()

    def test_preserves_all_fields(self, chain_file: Path) -> None:
        entry = record_entry(
            task_id="T05",
            stage="review",
            agent="code-reviewer",
            input_data="test input",
            output_data="test output",
            description="Code review of T05",
            pipeline="execute",
            verdict="PASS",
            warnings=["scope warning"],
            metadata={"review_cycle": 1},
            chain_path=chain_file,
        )
        assert entry["task_id"] == "T05"
        assert entry["stage"] == "review"
        assert entry["agent"] == "code-reviewer"
        assert entry["pipeline"] == "execute"
        assert entry["verdict"] == "PASS"
        assert entry["warnings"] == ["scope warning"]
        assert entry["metadata"] == {"review_cycle": 1}
        assert entry["description"] == "Code review of T05"
        assert "timestamp" in entry

    def test_hashes_are_deterministic(self, chain_file: Path) -> None:
        """Same input/output data produces same hashes."""
        entry = record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="fixed input", output_data="fixed output",
            description="test",
            chain_path=chain_file,
        )
        assert entry["input_hash"] == hash_content("fixed input")
        assert entry["output_hash"] == hash_content("fixed output")

    def test_default_empty_warnings_and_metadata(self, chain_file: Path) -> None:
        entry = record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="in", output_data="out", description="test",
            chain_path=chain_file,
        )
        assert entry["warnings"] == []
        assert entry["metadata"] == {}

    def test_json_file_is_valid(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="in", output_data="out", description="test",
            chain_path=chain_file,
        )
        data = json.loads(chain_file.read_text(encoding="utf-8"))
        assert "_schema" in data
        assert "entries" in data
        assert len(data["entries"]) == 1


# ---------------------------------------------------------------------------
# verify_integrity
# ---------------------------------------------------------------------------


class TestVerifyIntegrity:
    def test_empty_chain_is_valid(self, chain_file: Path) -> None:
        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is True
        assert broken == []

    def test_valid_chain(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="1",
            chain_path=chain_file,
        )
        record_entry(
            task_id="T01", stage="review", agent="code-reviewer",
            input_data="c", output_data="d", description="2",
            chain_path=chain_file,
        )
        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is True
        assert broken == []

    def test_detects_tampered_output_hash(self, chain_file: Path) -> None:
        """Corrupting an output_hash breaks the chain at the next entry."""
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="1",
            chain_path=chain_file,
        )
        record_entry(
            task_id="T01", stage="review", agent="code-reviewer",
            input_data="c", output_data="d", description="2",
            chain_path=chain_file,
        )

        # Tamper: change first entry's output_hash
        data = json.loads(chain_file.read_text(encoding="utf-8"))
        data["entries"][0]["output_hash"] = "sha256:TAMPERED"
        chain_file.write_text(json.dumps(data), encoding="utf-8")

        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is False
        assert len(broken) == 1
        assert "Entry 2" in broken[0]
        assert "mismatch" in broken[0]

    def test_detects_corrupted_first_entry_prev_hash(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="1",
            chain_path=chain_file,
        )

        data = json.loads(chain_file.read_text(encoding="utf-8"))
        data["entries"][0]["prev_hash"] = "sha256:SHOULD_BE_NULL"
        chain_file.write_text(json.dumps(data), encoding="utf-8")

        valid, broken = verify_integrity(chain_path=chain_file)
        assert valid is False
        assert len(broken) == 1
        assert "Entry 1" in broken[0]

    def test_updates_integrity_metadata(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="1",
            chain_path=chain_file,
        )
        verify_integrity(chain_path=chain_file)

        data = json.loads(chain_file.read_text(encoding="utf-8"))
        assert data["integrity"]["last_verified"] is not None
        assert data["integrity"]["chain_valid"] is True
        assert data["integrity"]["broken_links"] == []

    def test_nonexistent_file_is_valid(self, tmp_path: Path) -> None:
        """Missing chain file = empty chain = valid."""
        valid, broken = verify_integrity(chain_path=tmp_path / "missing.json")
        assert valid is True
        assert broken == []


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_empty_chain_message(self, chain_file: Path) -> None:
        result = get_summary(chain_path=chain_file)
        assert "empty" in result.lower()

    def test_no_entries_for_task(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="test",
            chain_path=chain_file,
        )
        result = get_summary(task_id="T99", chain_path=chain_file)
        assert "T99" in result
        assert "No chain entries" in result

    def test_shows_all_entries(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="first",
            chain_path=chain_file,
        )
        record_entry(
            task_id="T02", stage="review", agent="code-reviewer",
            input_data="c", output_data="d", description="second",
            chain_path=chain_file,
        )
        result = get_summary(chain_path=chain_file)
        assert "Chain entries: 2" in result
        assert "first" in result
        assert "second" in result

    def test_filters_by_task(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="verify", agent="self",
            input_data="a", output_data="b", description="task one",
            chain_path=chain_file,
        )
        record_entry(
            task_id="T02", stage="verify", agent="self",
            input_data="c", output_data="d", description="task two",
            chain_path=chain_file,
        )
        result = get_summary(task_id="T01", chain_path=chain_file)
        assert "Chain entries: 1" in result
        assert "task one" in result
        assert "task two" not in result

    def test_shows_verdict(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="review", agent="code-reviewer",
            input_data="a", output_data="b", description="test",
            verdict="BLOCK",
            chain_path=chain_file,
        )
        result = get_summary(chain_path=chain_file)
        assert "BLOCK" in result

    def test_shows_warnings(self, chain_file: Path) -> None:
        record_entry(
            task_id="T01", stage="review", agent="code-reviewer",
            input_data="a", output_data="b", description="test",
            warnings=["scope violation"],
            chain_path=chain_file,
        )
        result = get_summary(chain_path=chain_file)
        assert "scope violation" in result


# ---------------------------------------------------------------------------
# CLI (main)
# ---------------------------------------------------------------------------


class TestCLI:
    def test_verify_empty(self, chain_file: Path) -> None:
        ret = main(["--chain-file", str(chain_file), "verify"])
        assert ret == 0

    def test_summary_empty(self, chain_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--chain-file", str(chain_file), "summary"])
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()

    def test_record_and_verify(self, chain_file: Path, tmp_path: Path) -> None:
        in_file = tmp_path / "in.txt"
        out_file = tmp_path / "out.txt"
        in_file.write_text("input data", encoding="utf-8")
        out_file.write_text("output data", encoding="utf-8")

        ret = main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T01",
            "--stage", "verify",
            "--agent", "self",
            "--input-file", str(in_file),
            "--output-file", str(out_file),
            "--description", "Test record",
        ])
        assert ret == 0
        assert chain_file.exists()

        ret = main(["--chain-file", str(chain_file), "verify"])
        assert ret == 0

    def test_record_with_all_options(self, chain_file: Path, tmp_path: Path) -> None:
        in_file = tmp_path / "in.txt"
        out_file = tmp_path / "out.txt"
        in_file.write_text("input", encoding="utf-8")
        out_file.write_text("output", encoding="utf-8")

        ret = main([
            "--chain-file", str(chain_file),
            "record",
            "--task", "T05",
            "--stage", "review",
            "--agent", "code-reviewer",
            "--input-file", str(in_file),
            "--output-file", str(out_file),
            "--description", "Code review",
            "--pipeline", "execute",
            "--verdict", "PASS",
            "--metadata", '{"review_cycle": 1}',
        ])
        assert ret == 0

        data = json.loads(chain_file.read_text(encoding="utf-8"))
        entry = data["entries"][0]
        assert entry["pipeline"] == "execute"
        assert entry["verdict"] == "PASS"
        assert entry["metadata"] == {"review_cycle": 1}

    def test_summary_with_task_filter(
        self, chain_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        in_file = tmp_path / "in.txt"
        out_file = tmp_path / "out.txt"
        in_file.write_text("input", encoding="utf-8")
        out_file.write_text("output", encoding="utf-8")

        main([
            "--chain-file", str(chain_file),
            "record", "--task", "T01", "--stage", "verify",
            "--agent", "self", "--input-file", str(in_file),
            "--output-file", str(out_file), "--description", "test",
        ])

        main(["--chain-file", str(chain_file), "summary", "--task", "T01"])
        captured = capsys.readouterr()
        assert "T01" in captured.out
