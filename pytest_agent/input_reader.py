"""Leitura e validação da entrada (Source_Input) do Agente."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from pytest_agent.errors import InputError

_MODULE_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,99}")


@dataclass(frozen=True)
class SourceInput:
    code: str
    module_name: str
    from_file: bool


def is_valid_module_name(name: str) -> bool:
    """Retorna True se `name` é um identificador válido (1 a 100 caracteres ASCII)."""
    return isinstance(name, str) and _MODULE_NAME_RE.fullmatch(name) is not None


def _read_file(path: Path) -> str:
    if path.is_dir():  # no Windows, abrir diretório gera PermissionError
        raise InputError(f"Não foi possível ler '{path}': o caminho é um diretório.")
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        raise InputError(f"Arquivo não encontrado: {path}") from None
    except PermissionError:
        raise InputError(f"Não foi possível ler o arquivo '{path}': permissão negada.") from None
    except IsADirectoryError:
        raise InputError(f"Não foi possível ler '{path}': o caminho é um diretório.") from None
    except UnicodeDecodeError:
        raise InputError(
            f"Não foi possível ler o arquivo '{path}': conteúdo não é UTF-8 válido."
        ) from None
    except OSError as exc:
        raise InputError(
            f"Não foi possível ler o arquivo '{path}': {exc.strerror or 'erro de E/S'}."
        ) from None


def _read_stdin(stdin: TextIO | None) -> str:
    if stdin is None:
        return ""
    isatty = getattr(stdin, "isatty", None)
    if callable(isatty) and isatty():
        return ""
    try:
        return stdin.read()
    except UnicodeDecodeError:
        raise InputError("Não foi possível ler a entrada padrão: conteúdo não é UTF-8 válido.") from None


def read_source(
    file: str | None, snippet: str | None, stdin: TextIO | None
) -> tuple[str, Path | None]:
    """Resolve a fonte única de código. Retorna (código, caminho do arquivo ou None).

    Lê a entrada padrão apenas se não for um TTY. Conteúdo não vazio vindo
    do stdin junto de outra fonte é um erro.
    """
    multiple_msg = (
        "Informe apenas uma fonte de entrada: arquivo, --snippet ou entrada padrão (stdin)."
    )
    if file is not None and snippet is not None:
        raise InputError(multiple_msg)

    stdin_text = _read_stdin(stdin)

    if file is not None:
        if stdin_text.strip():
            raise InputError(multiple_msg)
        path = Path(file)
        return _read_file(path), path

    if snippet is not None:
        if stdin_text.strip():
            raise InputError(multiple_msg)
        return snippet, None

    return stdin_text, None


def check_source(code: str) -> None:
    """Rejeita código vazio ou com erro de sintaxe (informando a linha)."""
    if not code.strip():
        raise InputError("A entrada está vazia: informe código Python para gerar os testes.")
    try:
        ast.parse(code)
    except SyntaxError as exc:
        raise InputError(
            f"Erro de sintaxe no código de entrada, na linha {exc.lineno}: {exc.msg}"
        ) from None
    except ValueError as exc:  # ex.: bytes nulos no código
        raise InputError(f"Código de entrada inválido: {exc}") from None


def resolve_module_name(file: Path | None, module_name: str | None) -> str:
    """Define o nome do módulo: nome do arquivo (sem extensão) ou --module-name."""
    if file is not None:
        name = file.stem
    elif module_name is None:
        raise InputError(
            "O nome do módulo é obrigatório para snippet ou entrada padrão: use --module-name."
        )
    else:
        name = module_name
    if not is_valid_module_name(name):
        raise InputError(
            f"Nome de módulo inválido: '{name}'. Use apenas letras, dígitos e sublinhados, "
            "sem começar por dígito, com 1 a 100 caracteres."
        )
    return name
