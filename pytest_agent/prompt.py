"""Construção dos prompts enviados ao modelo.

Este módulo não depende de LangChain: usa apenas o dataclass ``Message``.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


SYSTEM_PROMPT = """\
You are an expert Python developer who writes pytest test files.

Write pytest tests for the Python source code provided by the user.

Rules:
1. Use pytest. The very first line of your answer must be exactly `import pytest`, with no blank lines or text before it.
2. Import the code under test with `from <module_name> import ...`, where <module_name> is the module name given by the user.
3. For every public module-level function (a function whose name does not start with an underscore), write at least one success test and at least one failure test. Write failure tests with `pytest.raises` (or `pytest.warns` / `pytest.fail` when more appropriate).
4. Name every test function with the `test_` prefix.
5. Return only Python code. Do not use Markdown code fences (no line starting with three backticks) and do not write any text outside Python code or Python comments.
"""

_USER_TEMPLATE = """\
Module name: {module_name}

Write the pytest test file for the module `{module_name}`. Import the code under test with `from {module_name} import ...`.

Source code of the module:
<source>
{source_code}
</source>
"""

_RETRY_TEMPLATE = """\
The previous answer is invalid. Validation error: {error}

Return the complete corrected pytest test file. Start with `import pytest`, return only Python code and use no Markdown fences.
"""


def build_messages(source_code: str, module_name: str) -> list[Message]:
    """Monta as mensagens iniciais (system + user) para gerar os testes."""
    user = _USER_TEMPLATE.format(module_name=module_name, source_code=source_code)
    return [Message("system", SYSTEM_PROMPT), Message("user", user)]


def build_retry_messages(
    previous: list[Message], bad_output: str, error: str
) -> list[Message]:
    """Acrescenta a saída inválida e o erro de validação para pedir correção."""
    return [
        *previous,
        Message("assistant", bad_output),
        Message("user", _RETRY_TEMPLATE.format(error=error)),
    ]
