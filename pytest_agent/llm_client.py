"""Cliente do Azure OpenAI via LangChain.

Este módulo só depende de `config`, `errors` e `prompt` (para `Message`).
As mensagens de erro nunca reproduzem o texto bruto do SDK nem a chave de API.
"""

from __future__ import annotations

from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from pytest_agent.config import AzureConfig
from pytest_agent.errors import LlmError
from pytest_agent.prompt import Message

TIMEOUT_SECONDS = 60


class LlmClient(Protocol):
    """Contrato mínimo usado pelo orquestrador (e por fakes nos testes)."""

    def generate(self, messages: list[Message]) -> str: ...


def map_exception(exc: BaseException) -> LlmError:
    """Converte uma exceção do SDK em `LlmError` com mensagem pt-BR fixa."""
    # APITimeoutError herda de APIConnectionError: testar o timeout primeiro.
    if isinstance(exc, APITimeoutError):
        return LlmError(
            f"Tempo limite excedido: o modelo não respondeu em {TIMEOUT_SECONDS} segundos.",
            category="timeout",
        )
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return LlmError(
            "Falha de autenticação no Azure OpenAI. Verifique a chave de API e o "
            "endpoint configurados.",
            category="autenticação",
        )
    if isinstance(exc, RateLimitError):
        return LlmError(
            "Cota ou limite de requisições do Azure OpenAI excedido. "
            "Aguarde um pouco ou verifique a cota do deployment.",
            category="cota",
        )
    if isinstance(exc, APIConnectionError):
        return LlmError(
            "Falha de rede ao conectar ao Azure OpenAI. Verifique a conexão e o endpoint.",
            category="rede",
        )
    return LlmError(
        "Erro inesperado ao chamar o Azure OpenAI.",
        category="desconhecido",
    )


def _to_langchain(message: Message) -> BaseMessage:
    if message.role == "system":
        return SystemMessage(content=message.content)
    if message.role == "assistant":
        return AIMessage(content=message.content)
    return HumanMessage(content=message.content)


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts)
    return ""


class AzureLlmClient:
    """Implementação de `LlmClient` sobre `AzureChatOpenAI`."""

    def __init__(
        self,
        config: AzureConfig,
        temperature: float = 0.0,
        timeout_s: float = float(TIMEOUT_SECONDS),
    ) -> None:
        self._model = AzureChatOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            azure_deployment=config.deployment_name,
            temperature=temperature,
            timeout=timeout_s,
            max_retries=0,
        )

    @classmethod
    def from_config(cls, config: AzureConfig) -> "AzureLlmClient":
        return cls(config)

    def generate(self, messages: list[Message]) -> str:
        try:
            response = self._model.invoke([_to_langchain(m) for m in messages])
        except LlmError:
            raise
        except Exception as exc:  # noqa: BLE001 - mapeado para erro de domínio
            # `from None` evita que o texto bruto do SDK vaze na cadeia de exceções.
            raise map_exception(exc) from None
        return _content_to_text(response.content)
