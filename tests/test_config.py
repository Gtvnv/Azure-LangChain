"""Testes unitários do carregamento de configuração (.env e precedência)."""

import os

import pytest

from pytest_agent.config import REQUIRED_VARS, load_config

SECRET = "chave-super-secreta-123"


def _track_env(monkeypatch):
    """Registra as variáveis no monkeypatch para que o que load_dotenv
    gravar em os.environ seja removido ao final do teste."""
    for name in REQUIRED_VARS:
        monkeypatch.setenv(name, "provisorio")
        monkeypatch.delenv(name)


def _write_env(path, **overrides):
    values = {
        "AZURE_OPENAI_API_KEY": SECRET,
        "AZURE_OPENAI_ENDPOINT": "https://exemplo.openai.azure.com/",
        "AZURE_OPENAI_API_VERSION": "2024-02-01",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-dep",
    }
    values.update(overrides)
    path.write_text(
        "\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8"
    )


def test_carrega_variaveis_do_arquivo_env(tmp_path, monkeypatch):
    _track_env(monkeypatch)
    env_file = tmp_path / ".env"
    _write_env(env_file)

    config = load_config(dotenv_path=env_file)

    assert config.api_key == SECRET
    assert config.endpoint == "https://exemplo.openai.azure.com/"
    assert config.api_version == "2024-02-01"
    assert config.deployment_name == "gpt-dep"


def test_carrega_env_do_diretorio_atual_por_padrao(tmp_path, monkeypatch):
    _track_env(monkeypatch)
    _write_env(tmp_path / ".env")
    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert config.api_key == SECRET


def test_variavel_do_processo_tem_precedencia_sobre_env(tmp_path, monkeypatch):
    _track_env(monkeypatch)
    env_file = tmp_path / ".env"
    _write_env(env_file)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://processo.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "dep-processo")

    config = load_config(dotenv_path=env_file)

    assert config.endpoint == "https://processo.openai.azure.com/"
    assert config.deployment_name == "dep-processo"
    # variáveis não definidas no processo vêm do .env
    assert config.api_key == SECRET
    assert config.api_version == "2024-02-01"
    assert os.environ["AZURE_OPENAI_ENDPOINT"] == "https://processo.openai.azure.com/"


def test_sem_env_e_sem_variaveis_levanta_config_error(tmp_path, monkeypatch):
    _track_env(monkeypatch)
    from pytest_agent.errors import ConfigError

    with pytest.raises(ConfigError) as exc:
        load_config(dotenv_path=tmp_path / "inexistente.env")

    for name in REQUIRED_VARS:
        assert name in str(exc.value)
    assert ".env.example" in str(exc.value)


def test_repr_da_config_oculta_a_chave():
    config = load_config(
        env={
            "AZURE_OPENAI_API_KEY": SECRET,
            "AZURE_OPENAI_ENDPOINT": "https://exemplo.openai.azure.com/",
            "AZURE_OPENAI_API_VERSION": "2024-02-01",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-dep",
        }
    )

    text = repr(config)

    assert SECRET not in text
    assert "api_key" not in text
    assert "https://exemplo.openai.azure.com/" in text
    assert SECRET not in str(config)


def test_mensagem_de_erro_nao_contem_a_chave():
    from pytest_agent.errors import ConfigError

    with pytest.raises(ConfigError) as exc:
        load_config(env={"AZURE_OPENAI_API_KEY": SECRET})

    assert SECRET not in str(exc.value)
