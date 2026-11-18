"""Carregamento da configuração do Azure OpenAI a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from pytest_agent.errors import ConfigError

REQUIRED_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
)


@dataclass(frozen=True)
class AzureConfig:
    api_key: str = field(repr=False)
    endpoint: str
    api_version: str
    deployment_name: str


def load_config(
    env: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> AzureConfig:
    """Lê a configuração.

    Com ``env=None`` carrega o ``.env`` (sem sobrescrever variáveis já
    definidas no processo) e lê ``os.environ``. Com um mapeamento, não toca
    em arquivo nem em estado global.
    """
    if env is None:
        load_dotenv(dotenv_path or Path.cwd() / ".env", override=False)
        env = os.environ

    values = {name: (env.get(name) or "") for name in REQUIRED_VARS}
    missing = [name for name in REQUIRED_VARS if not values[name].strip()]
    if missing:
        raise ConfigError(
            "Variáveis de ambiente ausentes ou vazias: "
            + ", ".join(missing)
            + ". Copie .env.example para .env e preencha os valores."
        )

    return AzureConfig(
        api_key=values["AZURE_OPENAI_API_KEY"],
        endpoint=values["AZURE_OPENAI_ENDPOINT"],
        api_version=values["AZURE_OPENAI_API_VERSION"],
        deployment_name=values["AZURE_OPENAI_DEPLOYMENT_NAME"],
    )
