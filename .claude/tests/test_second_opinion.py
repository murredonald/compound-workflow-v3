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
    build_user_message,
    get_system_prompt,
    load_env,
    resolve_api_key,
    PROVIDER_DEFAULTS,
    API_KEY_NAMES,
    SYSTEM_PROMPT_SINGLE,
    SYSTEM_PROMPT_ORTHOGONAL,
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
            "OPENAI_API_KEY=sk-proj-abc123def456\n", encoding="utf-8"
        )
        result = load_env(env_file)
        assert result["OPENAI_API_KEY"] == "sk-proj-abc123def456"

    def test_gemini_key_format(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n",
            encoding="utf-8",
        )
        result = load_env(env_file)
        assert result["GEMINI_API_KEY"] == "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"


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
        env_vars = {"OPENAI_API_KEY": "sk-test-123"}
        result = resolve_api_key("openai", env_vars)
        assert result == "sk-test-123"

    def test_resolves_gemini_from_env_vars(self) -> None:
        env_vars = {"GEMINI_API_KEY": "AIza-test-456"}
        result = resolve_api_key("gemini", env_vars)
        assert result == "AIza-test-456"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-from-os"}, clear=False)
    def test_falls_back_to_os_environ(self) -> None:
        result = resolve_api_key("openai", {})
        assert result == "sk-from-os"

    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIza-from-os"}, clear=False)
    def test_falls_back_to_os_environ_gemini(self) -> None:
        result = resolve_api_key("gemini", {})
        assert result == "AIza-from-os"

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_exits(self) -> None:
        with pytest.raises(SystemExit):
            resolve_api_key("openai", {})

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_gemini_key_exits(self) -> None:
        with pytest.raises(SystemExit):
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
        mock_client_class.assert_called_once_with(api_key="fake-gemini-key")

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
