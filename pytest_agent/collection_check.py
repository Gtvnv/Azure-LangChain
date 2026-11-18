"""Verificação de coleta (pytest --collect-only) do conteúdo gerado."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

COLLECT_TIMEOUT_S = 30.0
_ENV_PREFIX = "AZURE_OPENAI_"


@dataclass(frozen=True)
class CollectionResult:
    ok: bool
    output: str = ""


Collector = Callable[[str, str, str], CollectionResult]


def build_collect_command(python_exe: str, test_path: str, ini_path: str) -> list[str]:
    return [
        python_exe,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        "-c",
        ini_path,
        test_path,
    ]


def summarize_output(text: str, max_lines: int = 20, max_chars: int = 2000) -> str:
    lines = text.strip().splitlines()
    summary = "\n".join(lines[-max_lines:])
    if len(summary) > max_chars:
        summary = summary[-max_chars:]
    return summary


def build_collect_env(base: Mapping[str, str]) -> dict[str, str]:
    env = {k: v for k, v in base.items() if not k.upper().startswith(_ENV_PREFIX)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def collect_with_pytest(
    test_content: str,
    module_name: str,
    source_code: str,
    *,
    timeout_s: float = COLLECT_TIMEOUT_S,
    run=subprocess.run,
) -> CollectionResult:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            test_file = tmp_dir / f"test_{module_name}.py"
            ini_file = tmp_dir / "pytest.ini"
            (tmp_dir / f"{module_name}.py").write_text(source_code, encoding="utf-8")
            test_file.write_text(test_content, encoding="utf-8")
            ini_file.write_text("", encoding="utf-8")
            command = build_collect_command(sys.executable, str(test_file), str(ini_file))
            try:
                completed = run(
                    command,
                    cwd=str(tmp_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env=build_collect_env(os.environ),
                )
            except subprocess.TimeoutExpired:
                return CollectionResult(
                    ok=False,
                    output=(
                        "a coleta dos testes excedeu o limite de 30 segundos "
                        "(possível código de nível superior que não termina)"
                    ),
                )
            if completed.returncode == 0:
                return CollectionResult(ok=True)
            combined = (completed.stdout or "") + (completed.stderr or "")
            return CollectionResult(ok=False, output=summarize_output(combined))
    except OSError as exc:
        return CollectionResult(
            ok=False,
            output=f"não foi possível executar a coleta dos testes: {exc}",
        )
