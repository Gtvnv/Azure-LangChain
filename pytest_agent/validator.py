"""Extração e validação do conteúdo de testes gerado pelo modelo."""

from __future__ import annotations

import ast
from dataclasses import dataclass

IMPORT_LINE = "import pytest"
_FAILURE_CALLS = frozenset({"raises", "warns", "fail"})


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error: str | None = None


def _strip_line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith(("\n", "\r")):
        return line[:-1]
    return line


def _extract_fenced(raw: str) -> str | None:
    """Retorna o interior do primeiro bloco cercado, ou None se não houver cerca."""
    lines = raw.splitlines(keepends=True)
    for start, line in enumerate(lines):
        if line.startswith("```"):
            break
    else:
        return None
    for end in range(start + 1, len(lines)):
        if lines[end].startswith("```"):
            inner = lines[start + 1 : end]
            if inner:
                # A quebra de linha final pertence à cerca de fechamento.
                inner[-1] = _strip_line_ending(inner[-1])
            return "".join(inner)
    # Cerca sem fechamento: leva o restante do texto.
    return "".join(lines[start + 1 :])


def extract_code(raw: str) -> str:
    """Extrai o código de teste da resposta do modelo.

    1. Se houver bloco cercado (```), usa o interior do primeiro bloco.
    2. Depois descarta tudo antes da primeira linha ``import pytest``.
    """
    text = raw
    fenced = _extract_fenced(raw)
    if fenced is not None:
        text = fenced
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if _strip_line_ending(line).rstrip() == IMPORT_LINE:
            return "".join(lines[index:])
    return text


def _is_test_name(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")


def _has_test_function(tree: ast.Module) -> bool:
    for node in tree.body:
        if _is_test_name(node):
            return True
        if isinstance(node, ast.ClassDef) and any(_is_test_name(child) for child in node.body):
            return True
    return False


def _has_failure_assertion(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _FAILURE_CALLS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest"
        ):
            return True
    return False


def validate_module_import(content: str, module_name: str) -> ValidationResult:
    """Verifica se há ``from <module_name> import ...`` no nível superior."""
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return ValidationResult(
            False,
            f"O código gerado tem erro de sintaxe na linha {exc.lineno}: {exc.msg}.",
        )
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == module_name:
            return ValidationResult(True, None)
    return ValidationResult(
        False,
        f"O arquivo deve importar o módulo alvo no nível superior com "
        f"'from {module_name} import ...'.",
    )


def validate_test_content(content: str) -> ValidationResult:
    """Valida o conteúdo gerado, retornando a primeira falha encontrada."""
    lines = content.splitlines()
    if not lines or lines[0] != IMPORT_LINE:
        return ValidationResult(
            False,
            "A primeira linha do arquivo deve ser exatamente 'import pytest', "
            "sem espaços ou linhas em branco antes dela.",
        )
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return ValidationResult(
            False,
            f"O código gerado tem erro de sintaxe na linha {exc.lineno}: {exc.msg}.",
        )
    if not _has_test_function(tree):
        return ValidationResult(
            False,
            "O arquivo deve conter ao menos uma função 'test_*' no nível do módulo "
            "ou um método 'test_*' em uma classe de nível do módulo.",
        )
    if not _has_failure_assertion(tree):
        return ValidationResult(
            False,
            "O arquivo deve conter ao menos um teste de caso de falha usando "
            "'pytest.raises', 'pytest.warns' ou 'pytest.fail'.",
        )
    return ValidationResult(True, None)
