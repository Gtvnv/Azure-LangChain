"""Testes unitários da verificação de coleta (Requisitos 3.12-3.16, 9.9)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pytest_agent.collection_check import (
    CollectionResult,
    build_collect_command,
    build_collect_env,
    collect_with_pytest,
)


def test_build_collect_command_has_expected_arguments():
    cmd = build_collect_command("py", "t.py", "p.ini")
    assert cmd == [
        "py", "-m", "pytest", "--collect-only", "-q",
        "-p", "no:cacheprovider", "-c", "p.ini", "t.py",
    ]


def test_build_collect_env_removes_azure_vars_and_sets_no_bytecode():
    base = {"PATH": "x", "AZURE_OPENAI_API_KEY": "segredo", "azure_openai_endpoint": "e"}
    env = build_collect_env(base)
    assert env["PATH"] == "x"
    assert not any(k.upper().startswith("AZURE_OPENAI_") for k in env)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "AZURE_OPENAI_API_KEY" in base  # entrada não é mutada


def test_nonzero_return_code_gives_failure_with_output():
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="saida-out\n", stderr="erro-err\n")

    result = collect_with_pytest("x = 1\n", "mod", "", run=run)
    assert result.ok is False
    assert "saida-out" in result.output
    assert "erro-err" in result.output


def test_timeout_gives_failure_mentioning_30_seconds():
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30)

    result = collect_with_pytest("x = 1\n", "mod", "", run=run)
    assert result.ok is False
    assert "30" in result.output


def test_oserror_gives_failure_with_message():
    def run(*args, **kwargs):
        raise OSError("boom")

    result = collect_with_pytest("x = 1\n", "mod", "", run=run)
    assert result.ok is False
    assert "boom" in result.output


def test_real_subprocess_valid_import_is_ok():
    content = "from mod import f\n\n\ndef test_f():\n    assert f() == 1\n"
    result = collect_with_pytest(content, "mod", "def f():\n    return 1\n")
    assert result == CollectionResult(ok=True)


def test_real_subprocess_missing_name_fails_with_error_in_output():
    content = "from mod import inexistente\n\n\ndef test_x():\n    assert inexistente\n"
    result = collect_with_pytest(content, "mod", "def f():\n    return 1\n")
    assert result.ok is False
    assert "inexistente" in result.output


def test_temporary_directory_is_removed_afterwards():
    seen: list[str] = []

    def run(command, **kwargs):
        seen.append(kwargs["cwd"])
        assert Path(kwargs["cwd"]).is_dir()
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = collect_with_pytest("x = 1\n", "mod", "", run=run)
    assert result.ok is True
    assert seen and not Path(seen[0]).exists()
