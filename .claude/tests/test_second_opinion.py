"""Tests for .claude/tools/second_opinion.py — cross-model advisory perspective."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from second_opinion import (
    SecondOpinionError,
    build_user_message,
    build_code_review_message,
    build_diagnosis_message,
    build_debugging_message,
    get_system_prompt,
    load_env,
    resolve_api_key,
    PROVIDER_DEFAULTS,
    API_KEY_NAMES,
    SYSTEM_PROMPT_SINGLE,
    SYSTEM_PROMPT_ORTHOGONAL,
    SYSTEM_PROMPT_CODE_REVIEW,
    SYSTEM_PROMPT_DIAGNOSIS,
    SYSTEM_PROMPT_DEBUGGING,
    MODE_PROMPTS,
    MESSAGE_BUILDERS,
)


# ── load_env ─────────────────────────────────────────────────────

class TestLoadEnv:
    def test_load_basic_env(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
        result = load_env(env_file)
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_skip_comments_and_empty_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY=value\n", encoding="utf-8")
        result = load_env(env_file)
        assert result == {"KEY": "value"}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_env(tmp_path / "nonexistent")
        assert result == {}

    def test_value_with_equals_sign(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val=ue=with=equals\n", encoding="utf-8")
        result = load_env(env_file)
        assert result == {"KEY": "val=ue=with=equals"}

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("  KEY  =  value  \n", encoding="utf-8")
        result = load_env(env_file)
        assert result == {"KEY": "value"}

    def test_openai_key_format(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=test-openai-key-placeholder\n", encoding="utf-8"
        )
        result = load_env(env_file)
        assert result["OPENAI_API_KEY"] == "test-openai-key-placeholder"

    def test_gemini_key_format(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GEMINI_API_KEY=test-gemini-key-placeholder\n",
            encoding="utf-8",
        )
        result = load_env(env_file)
        assert result["GEMINI_API_KEY"] == "test-gemini-key-placeholder"


# ── build_user_message ───────────────────────────────────────────

class TestBuildUserMessage:
    def test_includes_all_sections(self) -> None:
        context = {
            "project_spec": "Test project",
            "decisions": "GEN-01: Test decision",
            "constraints": "Solo developer",
            "specialist_domain": "architecture",
            "focus_area": "Caching",
            "specialist_analysis": "Redis vs none",
            "questions": ["Use caching?", "Which strategy?"],
        }
        result = build_user_message(context)
        assert "## Project Specification" in result
        assert "Test project" in result
        assert "## Current Decisions" in result
        assert "GEN-01: Test decision" in result
        assert "## Constraints" in result
        assert "Solo developer" in result
        assert "## Specialist Domain: architecture" in result
        assert "## Focus Area: Caching" in result
        assert "## Specialist Analysis" in result
        assert "Redis vs none" in result
        assert "## Questions" in result
        assert "1. Use caching?" in result
        assert "2. Which strategy?" in result

    def test_handles_missing_fields(self) -> None:
        result = build_user_message({})
        assert "N/A" in result

    def test_handles_string_questions(self) -> None:
        context = {"questions": "Single question as string"}
        result = build_user_message(context)
        assert "Single question as string" in result

    def test_handles_empty_questions_list(self) -> None:
        context = {"questions": []}
        result = build_user_message(context)
        assert "## Questions" in result


# ── get_system_prompt ────────────────────────────────────────────

class TestGetSystemPrompt:
    def test_single_answer_returns_single_prompt(self) -> None:
        result = get_system_prompt(1)
        assert result == SYSTEM_PROMPT_SINGLE

    def test_zero_answers_returns_single_prompt(self) -> None:
        result = get_system_prompt(0)
        assert result == SYSTEM_PROMPT_SINGLE

    def test_negative_answers_returns_single_prompt(self) -> None:
        result = get_system_prompt(-1)
        assert result == SYSTEM_PROMPT_SINGLE

    def test_default_returns_single_prompt(self) -> None:
        result = get_system_prompt()
        assert result == SYSTEM_PROMPT_SINGLE

    def test_three_answers_returns_orthogonal_prompt(self) -> None:
        result = get_system_prompt(3)
        assert "3 genuinely different perspectives" in result
        assert "1050 words" in result  # 3 * 350
        assert "Perspective A" in result
        assert "Perspective B" in result
        assert "Perspective C" in result

    def test_two_answers_returns_orthogonal_prompt(self) -> None:
        result = get_system_prompt(2)
        assert "2 genuinely different perspectives" in result
        assert "700 words" in result  # 2 * 350

    def test_five_answers_returns_orthogonal_prompt(self) -> None:
        result = get_system_prompt(5)
        assert "5 genuinely different perspectives" in result
        assert "1750 words" in result  # 5 * 350

    def test_orthogonal_prompt_not_contrarian(self) -> None:
        result = get_system_prompt(3)
        assert "independently useful and defensible" in result
        assert "genuinely different" in result

    def test_orthogonal_prompt_has_perspective_labels(self) -> None:
        result = get_system_prompt(3)
        assert "Perspective A" in result
        assert "Perspective B" in result
        assert "Perspective C" in result


# ── resolve_api_key ──────────────────────────────────────────────

class TestResolveApiKey:
    def test_resolves_openai_from_env_vars(self) -> None:
        env_vars = {"OPENAI_API_KEY": "test-openai-key-123"}
        result = resolve_api_key("openai", env_vars)
        assert result == "test-openai-key-123"

    def test_resolves_gemini_from_env_vars(self) -> None:
        env_vars = {"GEMINI_API_KEY": "test-gemini-key-456"}
        result = resolve_api_key("gemini", env_vars)
        assert result == "test-gemini-key-456"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai-from-os"}, clear=False)
    def test_falls_back_to_os_environ(self) -> None:
        result = resolve_api_key("openai", {})
        assert result == "test-openai-from-os"

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-from-os"}, clear=False)
    def test_falls_back_to_os_environ_gemini(self) -> None:
        result = resolve_api_key("gemini", {})
        assert result == "test-gemini-from-os"

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_raises_error(self) -> None:
        with pytest.raises(SecondOpinionError, match="OPENAI_API_KEY"):
            resolve_api_key("openai", {})

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_gemini_key_raises_error(self) -> None:
        with pytest.raises(SecondOpinionError, match="GEMINI_API_KEY"):
            resolve_api_key("gemini", {})


# ── provider defaults & key names ────────────────────────────────

class TestProviderConfig:
    def test_provider_defaults(self) -> None:
        assert PROVIDER_DEFAULTS["openai"] == "gpt-4o"
        assert PROVIDER_DEFAULTS["gemini"] == "gemini-2.0-flash"

    def test_api_key_names(self) -> None:
        assert API_KEY_NAMES["openai"] == "OPENAI_API_KEY"
        assert API_KEY_NAMES["gemini"] == "GEMINI_API_KEY"


# ── CLI integration ──────────────────────────────────────────────

class TestCLI:
    def test_missing_context_file_exits_1(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--context-file",
                str(tmp_path / "nonexistent.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_missing_api_key_exits_1(self, tmp_path: Path) -> None:
        ctx = tmp_path / "ctx.json"
        ctx.write_text(
            json.dumps({"questions": ["test?"]}), encoding="utf-8"
        )
        env_file = tmp_path / ".env"
        env_file.write_text("# empty\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--context-file",
                str(ctx),
                "--env-file",
                str(env_file),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env={**dict(__import__("os").environ), "OPENAI_API_KEY": ""},
        )
        assert result.returncode == 1
        assert "OPENAI_API_KEY" in result.stderr

    def test_missing_gemini_key_exits_1(self, tmp_path: Path) -> None:
        ctx = tmp_path / "ctx.json"
        ctx.write_text(
            json.dumps({"questions": ["test?"]}), encoding="utf-8"
        )
        env_file = tmp_path / ".env"
        env_file.write_text("# empty\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--provider",
                "gemini",
                "--context-file",
                str(ctx),
                "--env-file",
                str(env_file),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env={**dict(__import__("os").environ), "GEMINI_API_KEY": ""},
        )
        assert result.returncode == 1
        assert "GEMINI_API_KEY" in result.stderr

    def test_help_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/second_opinion.py", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "--context-file" in result.stdout
        assert "--model" in result.stdout
        assert "--provider" in result.stdout
        assert "--answers" in result.stdout

    def test_invalid_provider_exits(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--provider",
                "invalid",
                "--context-file",
                "dummy.json",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode != 0


# ── call_openai (mocked) ────────────────────────────────────────

class TestCallOpenAI:
    @patch("openai.OpenAI")
    def test_call_openai_returns_content(self, mock_openai_class: MagicMock) -> None:
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "### Advisory Perspective: Test\n\n**Q1: Test?**\nAnswer."
        mock_client.chat.completions.create.return_value = mock_response

        result = call_openai("fake-key", "test message", model="gpt-4o")
        assert "Advisory Perspective" in result
        assert "Q1: Test?" in result

    @patch("openai.OpenAI")
    def test_call_openai_handles_none_content(self, mock_openai_class: MagicMock) -> None:
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        result = call_openai("fake-key", "test message")
        assert result == ""

    @patch("openai.OpenAI")
    def test_call_openai_passes_correct_params(self, mock_openai_class: MagicMock) -> None:
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_client.chat.completions.create.return_value = mock_response

        call_openai("test-key", "user msg", model="gpt-4o-mini", timeout=15)

        mock_openai_class.assert_called_once_with(api_key="test-key", timeout=15)
        create_call = mock_client.chat.completions.create.call_args
        assert create_call.kwargs["model"] == "gpt-4o-mini"
        assert len(create_call.kwargs["messages"]) == 2
        assert create_call.kwargs["messages"][0]["role"] == "system"
        assert create_call.kwargs["messages"][1]["content"] == "user msg"

    @patch("openai.OpenAI")
    def test_call_openai_uses_custom_system_prompt(self, mock_openai_class: MagicMock) -> None:
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "orthogonal output"
        mock_client.chat.completions.create.return_value = mock_response

        custom_prompt = "You provide 3 orthogonal perspectives."
        call_openai("key", "msg", system_prompt=custom_prompt)

        create_call = mock_client.chat.completions.create.call_args
        assert create_call.kwargs["messages"][0]["content"] == custom_prompt

    @patch("openai.OpenAI")
    def test_call_openai_defaults_to_single_prompt(self, mock_openai_class: MagicMock) -> None:
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_client.chat.completions.create.return_value = mock_response

        call_openai("key", "msg")

        create_call = mock_client.chat.completions.create.call_args
        assert create_call.kwargs["messages"][0]["content"] == SYSTEM_PROMPT_SINGLE


# ── call_gemini (mocked) ─────────────────────────────────────────

class TestCallGemini:
    @patch("google.genai.Client")
    def test_call_gemini_returns_content(self, mock_client_class: MagicMock) -> None:
        from second_opinion import call_gemini

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "### Advisory Perspective: Test\n\n**Q1: Test?**\nGemini answer."
        mock_client.models.generate_content.return_value = mock_response

        result = call_gemini("fake-gemini-key", "test message")
        assert "Advisory Perspective" in result
        assert "Gemini answer" in result
        mock_client_class.assert_called_once_with(
            api_key="fake-gemini-key", http_options={"timeout": 90_000}
        )

    @patch("google.genai.Client")
    def test_call_gemini_handles_none_text(self, mock_client_class: MagicMock) -> None:
        from second_opinion import call_gemini

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response

        result = call_gemini("fake-key", "test message")
        assert result == ""

    @patch("google.genai.Client")
    def test_call_gemini_passes_correct_model(self, mock_client_class: MagicMock) -> None:
        from second_opinion import call_gemini

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "test"
        mock_client.models.generate_content.return_value = mock_response

        call_gemini("key", "msg", model="gemini-2.0-flash")

        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == "gemini-2.0-flash"

    @patch("google.genai.Client")
    def test_call_gemini_uses_custom_system_prompt(self, mock_client_class: MagicMock) -> None:
        from second_opinion import call_gemini

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "orthogonal output"
        mock_client.models.generate_content.return_value = mock_response

        custom_prompt = "You provide 3 orthogonal perspectives."
        call_gemini("key", "msg", system_prompt=custom_prompt)

        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]
        assert config.system_instruction == custom_prompt

    @patch("google.genai.Client")
    def test_call_gemini_defaults_to_single_prompt(self, mock_client_class: MagicMock) -> None:
        from second_opinion import call_gemini

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "test"
        mock_client.models.generate_content.return_value = mock_response

        call_gemini("key", "msg")

        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]
        assert config.system_instruction == SYSTEM_PROMPT_SINGLE


# ── Mode Prompts ─────────────────────────────────────────────────

class TestModePrompts:
    def test_mode_prompts_has_all_keys(self) -> None:
        assert set(MODE_PROMPTS.keys()) == {"planning", "code-review", "diagnosis", "debugging"}

    def test_planning_mode_is_sentinel(self) -> None:
        assert MODE_PROMPTS["planning"] == ""

    def test_code_review_prompt_has_keywords(self) -> None:
        prompt = SYSTEM_PROMPT_CODE_REVIEW
        assert "BUG" in prompt
        assert "SECURITY" in prompt
        assert "CRITICAL" in prompt
        assert "MAJOR" in prompt
        assert "MINOR" in prompt
        assert "file:line" in prompt

    def test_diagnosis_prompt_has_categories(self) -> None:
        prompt = SYSTEM_PROMPT_DIAGNOSIS
        assert "CODE_BUG" in prompt
        assert "TEST_BUG" in prompt
        assert "MISSING_IMPL" in prompt
        assert "ENV_ISSUE" in prompt
        assert "FLAKY" in prompt

    def test_debugging_prompt_has_hypothesis_format(self) -> None:
        prompt = SYSTEM_PROMPT_DEBUGGING
        assert "H1" in prompt
        assert "H2" in prompt
        assert "Mechanism" in prompt
        assert "Test method" in prompt


# ── build_code_review_message ────────────────────────────────────

class TestBuildCodeReviewMessage:
    def test_includes_task_and_diff(self) -> None:
        context = {
            "task_id": "T05",
            "task_definition": "Add login endpoint",
            "git_diff": "diff --git a/api.py b/api.py\n+@app.route('/login')",
            "decisions": "BACK-01: Use FastAPI",
            "constraints": "Solo developer",
        }
        result = build_code_review_message(context)
        assert "## Task: T05" in result
        assert "Add login endpoint" in result
        assert "diff --git" in result
        assert "BACK-01" in result
        assert "Solo developer" in result

    def test_handles_missing_optional_fields(self) -> None:
        context = {
            "task_id": "T01",
            "task_definition": "Fix bug",
            "git_diff": "+ fixed line",
        }
        result = build_code_review_message(context)
        assert "## Task: T01" in result
        assert "Fix bug" in result
        assert "Decisions" not in result
        assert "Constraints" not in result

    def test_handles_empty_context(self) -> None:
        result = build_code_review_message({})
        assert "N/A" in result


# ── build_diagnosis_message ──────────────────────────────────────

class TestBuildDiagnosisMessage:
    def test_includes_test_output(self) -> None:
        context = {
            "test_output": "FAILED test_login - AssertionError",
            "task_context": "Implementing auth",
            "recent_changes": "auth.py, routes.py",
        }
        result = build_diagnosis_message(context)
        assert "FAILED test_login" in result
        assert "Implementing auth" in result
        assert "auth.py" in result

    def test_handles_missing_optional_fields(self) -> None:
        context = {
            "test_output": "3 failed",
            "task_context": "Adding tests",
        }
        result = build_diagnosis_message(context)
        assert "3 failed" in result
        assert "Recent Changes" not in result

    def test_handles_empty_context(self) -> None:
        result = build_diagnosis_message({})
        assert "N/A" in result


# ── build_debugging_message ──────────────────────────────────────

class TestBuildDebuggingMessage:
    def test_includes_bug_and_hypotheses(self) -> None:
        context = {
            "bug_description": "Login returns 500 on special characters",
            "reproduction_steps": "1. Enter 'user@test' 2. Click login",
            "current_hypotheses": "H1: SQL injection in login query",
        }
        result = build_debugging_message(context)
        assert "Login returns 500" in result
        assert "Enter 'user@test'" in result
        assert "H1: SQL injection" in result

    def test_handles_missing_optional_fields(self) -> None:
        context = {
            "bug_description": "App crashes on startup",
        }
        result = build_debugging_message(context)
        assert "App crashes" in result
        assert "Reproduction" not in result

    def test_handles_empty_context(self) -> None:
        result = build_debugging_message({})
        assert "N/A" in result


# ── MESSAGE_BUILDERS dict ────────────────────────────────────────

class TestMessageBuilders:
    def test_has_all_modes(self) -> None:
        assert set(MESSAGE_BUILDERS.keys()) == {"planning", "code-review", "diagnosis", "debugging"}

    def test_planning_maps_to_original_builder(self) -> None:
        assert MESSAGE_BUILDERS["planning"] is build_user_message

    def test_code_review_maps_to_correct_builder(self) -> None:
        assert MESSAGE_BUILDERS["code-review"] is build_code_review_message

    def test_diagnosis_maps_to_correct_builder(self) -> None:
        assert MESSAGE_BUILDERS["diagnosis"] is build_diagnosis_message

    def test_debugging_maps_to_correct_builder(self) -> None:
        assert MESSAGE_BUILDERS["debugging"] is build_debugging_message


# ── CLI --mode flag ──────────────────────────────────────────────

class TestCLIMode:
    def test_help_shows_mode_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/second_opinion.py", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "--mode" in result.stdout
        assert "code-review" in result.stdout
        assert "diagnosis" in result.stdout
        assert "debugging" in result.stdout

    def test_invalid_mode_exits_nonzero(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--mode",
                "invalid",
                "--context-file",
                "dummy.json",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode != 0


# ── v3.15: Corrupted context file ────────────────────────────────

class TestCorruptedContextFile:
    """Test handling of malformed context JSON files."""

    def test_corrupted_context_file_exits_1(self, tmp_path: Path) -> None:
        """CLI exits 1 with clear error for malformed JSON context file."""
        ctx = tmp_path / "bad.json"
        ctx.write_text("{not valid json!!!", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--context-file",
                str(ctx),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 1
        assert "malformed" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_empty_context_file_exits_1(self, tmp_path: Path) -> None:
        """CLI exits 1 for empty context file."""
        ctx = tmp_path / "empty.json"
        ctx.write_text("", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "tools/second_opinion.py",
                "--context-file",
                str(ctx),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 1


# ── v3.15: SecondOpinionError for library functions ───────────────

class TestSecondOpinionErrorRaised:
    """Test that SecondOpinionError is raised (not SystemExit) by library functions."""

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_openai_key_raises_error(self) -> None:
        """resolve_api_key raises SecondOpinionError for missing OpenAI key."""
        with pytest.raises(SecondOpinionError, match="OPENAI_API_KEY"):
            resolve_api_key("openai", {})

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_gemini_key_raises_error(self) -> None:
        """resolve_api_key raises SecondOpinionError for missing Gemini key."""
        with pytest.raises(SecondOpinionError, match="GEMINI_API_KEY"):
            resolve_api_key("gemini", {})

    @patch("openai.OpenAI")
    def test_call_openai_propagates_api_error(self, mock_openai_class: MagicMock) -> None:
        """call_openai propagates API exceptions (caught by retry logic in main)."""
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")
        with pytest.raises(Exception, match="Connection refused"):
            call_openai("fake-key", "test message")


# ── v3.15: Retry logic ───────────────────────────────────────────

class TestRetryLogic:
    """Test the retry-once-on-failure pattern."""

    @patch("openai.OpenAI")
    def test_retry_succeeds_on_second_attempt(self, mock_openai_class: MagicMock) -> None:
        """When first API call fails and second succeeds, second returns result."""
        from second_opinion import call_openai

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # First call raises, second succeeds
        mock_success = MagicMock()
        mock_success.choices = [MagicMock()]
        mock_success.choices[0].message.content = "Retry success"
        mock_client.chat.completions.create.side_effect = [
            Exception("Transient failure"),
            mock_success,
        ]

        # First call should fail
        with pytest.raises(Exception, match="Transient"):
            call_openai("fake-key", "test message")

        # Second call should succeed (side_effect consumed first exception)
        result = call_openai("fake-key", "test message")
        assert result == "Retry success"
