"""Testes unitários do prompt e do cliente LLM (Req 2.2, 2.3, 2.5, 2.6, 2.7)."""

import pytest

try:  # versões novas do SDK usam httpx2
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

import openai

from pytest_agent import llm_client
from pytest_agent.config import AzureConfig
from pytest_agent.errors import LlmError
from pytest_agent.llm_client import AzureLlmClient, map_exception
from pytest_agent.prompt import (
    SYSTEM_PROMPT,
    Message,
    build_messages,
    build_retry_messages,
)

_REQUEST = httpx.Request("POST", "https://exemplo.openai.azure.com/chat")


def _status_exc(cls, status):
    response = httpx.Response(status, request=_REQUEST)
    return cls("erro sintético com segredo-xyz", response=response, body=None)


CONFIG = AzureConfig(
    api_key="chave-secreta-123",
    endpoint="https://exemplo.openai.azure.com/",
    api_version="2024-06-01",
    deployment_name="meu-deploy",
)


# ---------------------------------------------------------------- prompt


def test_system_prompt_requires_success_and_failure_cases_for_public_functions():
    assert "at least one success test" in SYSTEM_PROMPT
    assert "at least one failure test" in SYSTEM_PROMPT
    assert "public module-level function" in SYSTEM_PROMPT
    assert "underscore" in SYSTEM_PROMPT
    assert "pytest.raises" in SYSTEM_PROMPT


def test_system_prompt_forbids_fences_and_non_code_text():
    assert "Return only Python code" in SYSTEM_PROMPT
    assert "Do not use Markdown code fences" in SYSTEM_PROMPT
    assert "outside Python code or Python comments" in SYSTEM_PROMPT


def test_system_prompt_requires_import_from_module():
    assert "from <module_name> import" in SYSTEM_PROMPT
    assert "import pytest" in SYSTEM_PROMPT


def test_build_messages_structure_contains_source_and_module():
    messages = build_messages("def f():\n    return 1\n", "meu_modulo")
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[0].content == SYSTEM_PROMPT
    assert "def f():\n    return 1\n" in messages[1].content
    assert "from meu_modulo import" in messages[1].content


def test_build_retry_messages_appends_bad_output_and_error():
    previous = build_messages("x = 1", "mod")
    retry = build_retry_messages(previous, "saida ruim", "erro de validação")
    assert retry[: len(previous)] == previous
    assert retry[-2] == Message("assistant", "saida ruim")
    assert retry[-1].role == "user"
    assert "erro de validação" in retry[-1].content


# ---------------------------------------------------------------- cliente


def test_azure_client_passes_required_parameters(monkeypatch):
    captured = {}

    class FakeChat:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm_client, "AzureChatOpenAI", FakeChat)
    AzureLlmClient(CONFIG)

    assert captured["temperature"] == 0
    assert captured["timeout"] == 60
    assert captured["max_retries"] == 0
    assert captured["azure_endpoint"] == CONFIG.endpoint
    assert captured["api_key"] == CONFIG.api_key
    assert captured["api_version"] == CONFIG.api_version
    assert captured["azure_deployment"] == CONFIG.deployment_name


def test_generate_returns_text_and_converts_roles(monkeypatch):
    seen = {}

    class Response:
        content = "import pytest\n"

    class FakeChat:
        def __init__(self, **kwargs):
            pass

        def invoke(self, msgs):
            seen["types"] = [type(m).__name__ for m in msgs]
            return Response()

    monkeypatch.setattr(llm_client, "AzureChatOpenAI", FakeChat)
    client = AzureLlmClient(CONFIG)
    out = client.generate(
        [Message("system", "s"), Message("user", "u"), Message("assistant", "a")]
    )
    assert out == "import pytest\n"
    assert seen["types"] == ["SystemMessage", "HumanMessage", "AIMessage"]


def test_generate_maps_sdk_errors_without_leaking_text(monkeypatch):
    class FakeChat:
        def __init__(self, **kwargs):
            pass

        def invoke(self, msgs):
            raise _status_exc(openai.AuthenticationError, 401)

    monkeypatch.setattr(llm_client, "AzureChatOpenAI", FakeChat)
    with pytest.raises(LlmError) as info:
        AzureLlmClient(CONFIG).generate([Message("user", "u")])
    assert info.value.category == "autenticação"
    assert "segredo-xyz" not in str(info.value)
    assert CONFIG.api_key not in str(info.value)


# ---------------------------------------------------------------- map_exception


def test_map_exception_authentication():
    err = map_exception(_status_exc(openai.AuthenticationError, 401))
    assert isinstance(err, LlmError)
    assert err.category == "autenticação"
    assert "autenticação" in str(err)


def test_map_exception_permission_denied_is_authentication():
    err = map_exception(_status_exc(openai.PermissionDeniedError, 403))
    assert err.category == "autenticação"


def test_map_exception_connection():
    err = map_exception(openai.APIConnectionError(request=_REQUEST))
    assert err.category == "rede"
    assert "rede" in str(err)


def test_map_exception_timeout_states_60_seconds():
    err = map_exception(openai.APITimeoutError(request=_REQUEST))
    assert err.category == "timeout"
    assert "60" in str(err)


def test_map_exception_rate_limit():
    err = map_exception(_status_exc(openai.RateLimitError, 429))
    assert err.category == "cota"
    assert "Cota" in str(err)


def test_map_exception_unknown_has_generic_category():
    err = map_exception(RuntimeError("segredo-xyz"))
    assert err.category == "desconhecido"
    assert "segredo-xyz" not in str(err)


def test_map_exception_exit_code_is_one():
    assert map_exception(RuntimeError()).exit_code == 1
