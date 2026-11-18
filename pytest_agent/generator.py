"""Orquestrador de geração: chama o modelo, limpa, valida e tenta novamente."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_agent.collection_check import Collector, collect_with_pytest
from pytest_agent.errors import LlmError, ValidationFailedError
from pytest_agent.prompt import build_messages, build_retry_messages
from pytest_agent.validator import (
    extract_code,
    validate_module_import,
    validate_test_content,
)

if TYPE_CHECKING:
    from pytest_agent.llm_client import LlmClient

MAX_RETRIES = 2


def generate_tests(
    source_code: str,
    module_name: str,
    llm: LlmClient,
    collector: Collector = collect_with_pytest,
) -> str:
    """Gera o conteúdo do arquivo de testes, com até ``1 + MAX_RETRIES`` tentativas.

    Erros de ``LlmError`` do cliente propagam sem nova tentativa. Resposta em
    branco gera ``LlmError`` de categoria "vazio" imediatamente.
    """
    messages = build_messages(source_code, module_name)
    last_error = "erro de validação desconhecido"

    for _attempt in range(1 + MAX_RETRIES):
        raw = llm.generate(messages)
        if not raw or not raw.strip():
            raise LlmError("O modelo retornou uma resposta vazia.", category="vazio")

        content = extract_code(raw)
        result = validate_test_content(content)
        if result.ok:
            result = validate_module_import(content, module_name)
        if result.ok:
            collected = collector(content, module_name, source_code)
            if collected.ok:
                return content
            last_error = (
                f"Falha na coleta do pytest (pytest --collect-only):\n{collected.output}"
                if collected.output
                else "Falha na coleta do pytest (pytest --collect-only)."
            )
        else:
            last_error = result.error or last_error
        messages = build_retry_messages(messages, raw, last_error)

    raise ValidationFailedError(
        f"O conteúdo gerado não passou na validação após {1 + MAX_RETRIES} tentativas. "
        f"Último erro: {last_error}"
    )

