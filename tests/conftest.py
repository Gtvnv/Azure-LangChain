import socket

import pytest

AZURE_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
)


def _blocked(*args, **kwargs):
    raise AssertionError("acesso à rede não permitido")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Impede qualquer conexão de rede durante os testes."""
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture(autouse=True)
def clean_azure_env(monkeypatch):
    """Remove as variáveis AZURE_OPENAI_* do ambiente de cada teste."""
    for name in AZURE_VARS:
        monkeypatch.delenv(name, raising=False)
