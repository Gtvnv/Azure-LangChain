"""Resolução do destino, confirmação de sobrescrita e gravação atômica."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from .errors import OutputError


def build_test_file_name(module_name: str) -> str:
    """Retorna o nome do arquivo de teste: ``test_<nome>.py``."""
    return f"test_{module_name}.py"


def resolve_target(output_dir: Path, module_name: str) -> Path:
    """Retorna o caminho completo do arquivo de teste no diretório de saída."""
    return Path(output_dir) / build_test_file_name(module_name)


def check_overwrite(
    target: Path,
    force: bool,
    is_interactive: bool,
    ask: Callable[[str], str],
) -> None:
    """Garante que o arquivo existente só seja substituído com autorização.

    Não faz nada se o destino não existe ou se ``force`` é verdadeiro.
    Levanta ``OutputError`` quando a sobrescrita não é confirmada.
    """
    if force or not target.exists():
        return

    if not is_interactive:
        raise OutputError(
            f"O arquivo '{target}' já existe e não há entrada interativa "
            "para confirmar a sobrescrita. Use --force para sobrescrever."
        )

    try:
        answer = ask(f"O arquivo '{target}' já existe. Sobrescrever? [s/N] ")
    except EOFError:
        raise OutputError(
            f"O arquivo '{target}' já existe e não foi possível ler a "
            "confirmação. Use --force para sobrescrever."
        ) from None

    if answer.strip().lower() not in ("s", "sim"):
        raise OutputError(
            f"Operação cancelada: o arquivo '{target}' não foi alterado."
        )


def write_test_file(target: Path, content: str) -> None:
    """Grava ``content`` em ``target`` de forma atômica (UTF-8, sem tradução de EOL)."""
    target = Path(target)
    directory = target.parent
    temp_path: str | None = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            dir=directory, prefix=f".{target.name}.", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_path, target)
        temp_path = None
    except OSError as exc:
        reason = exc.strerror or exc.__class__.__name__
        raise OutputError(
            f"Não foi possível gravar o arquivo de teste no diretório "
            f"'{directory}': {reason}."
        ) from exc
    finally:
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except OSError:
                pass
