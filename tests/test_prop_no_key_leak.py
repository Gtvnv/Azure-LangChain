"""Propriedade 12: a chave de API nunca aparece na saída."""

import contextlib
import io
import logging
import os
import tempfile
import traceback
from pathlib import Path

import httpx
import openai
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.cli import main
from pytest_agent.config import REQUIRED_VARS, load_config
from pytest_agent.errors import AgentError
from pytest_agent.llm_client import AzureLlmClient, map_exception
from tests.fakes import FakeLlm, RaisingFakeLlm, ok_collector

# Feature: pytest-test-generator-agent, Property 12: The API key never appears in output

VALID_CODE = "def f(a, b):\n    return a + b\n"

_keys = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
    min_size=8,
    max_size=40,
).filter(lambda k: any(c.isdigit() for c in k))

SCENARIOS = (
    "input_missing_file",
    "input_blank",
    "input_syntax",
    "input_two_sources",
    "input_bad_module_name",
    "config_missing",
    "llm_auth",
    "llm_network",
    "llm_quota",
    "llm_timeout",
    "llm_unexpected",
    "llm_blank",
    "validation_failure",
    "output_dir_is_file",
    "output_exists_noninteractive",
)


def _sdk_exception(kind, key):
    request = httpx.Request("POST", "https://recurso.openai.azure.com/")
    msg = f"falha com api-key={key}"
    if kind == "llm_auth":
        return openai.AuthenticationError(
            msg, response=httpx.Response(401, request=request), body={"key": key}
        )
    if kind == "llm_quota":
        return openai.RateLimitError(
            msg, response=httpx.Response(429, request=request), body={"key": key}
        )
    if kind == "llm_network":
        return openai.APIConnectionError(message=msg, request=request)
    if kind == "llm_timeout":
        return openai.APITimeoutError(request=request)
    return RuntimeError(msg)


class _SdkFailingModel:
    def __init__(self, exc):
        self.exc = exc

    def invoke(self, _messages):
        raise self.exc


def _client_failing_with(exc):
    client = AzureLlmClient.__new__(AzureLlmClient)
    client._model = _SdkFailingModel(exc)
    return client


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.texts = []

    def emit(self, record):
        self.texts.append(record.getMessage())
        self.texts.append(repr(record.__dict__.get("args")))
        if record.exc_info:
            self.texts.append("".join(traceback.format_exception(*record.exc_info)))


def _run_scenario(scenario, key, tmp):
    """Executa o cenário pela CLI e devolve todos os textos observáveis."""
    texts = []
    out_dir = tmp / "saida"
    argv = ["--snippet", VALID_CODE, "--module-name", "modulo", "--output-dir", str(out_dir)]
    env = {
        "AZURE_OPENAI_API_KEY": key,
        "AZURE_OPENAI_ENDPOINT": "https://recurso.openai.azure.com/",
        "AZURE_OPENAI_API_VERSION": "2024-06-01",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "dep",
    }
    llm = FakeLlm(["import pytest\n"])  # inválido por padrão

    if scenario == "input_missing_file":
        argv = [str(tmp / "nao_existe.py"), "--output-dir", str(out_dir)]
    elif scenario == "input_blank":
        argv = ["--snippet", "   ", "--module-name", "modulo", "--output-dir", str(out_dir)]
    elif scenario == "input_syntax":
        argv = ["--snippet", "def (:", "--module-name", "modulo", "--output-dir", str(out_dir)]
    elif scenario == "input_two_sources":
        src = tmp / "fonte.py"
        src.write_text(VALID_CODE, encoding="utf-8")
        argv = [str(src), "--snippet", VALID_CODE, "--output-dir", str(out_dir)]
    elif scenario == "input_bad_module_name":
        argv = ["--snippet", VALID_CODE, "--module-name", "1-ruim", "--output-dir", str(out_dir)]
    elif scenario == "config_missing":
        env = {k: v for k, v in env.items() if k != "AZURE_OPENAI_ENDPOINT"}
        env["AZURE_OPENAI_DEPLOYMENT_NAME"] = "   "
    elif scenario.startswith("llm_") and scenario != "llm_blank":
        exc = _sdk_exception(scenario, key)
        client = _client_failing_with(exc)
        # Caminho direto: mensagem, repr e traceback da exceção mapeada.
        try:
            client.generate([])
        except AgentError as err:
            texts += [str(err), repr(err), "".join(traceback.format_exception(err))]
        texts += [str(map_exception(exc)), repr(map_exception(exc))]
        llm = RaisingFakeLlm(map_exception(exc))
    elif scenario == "llm_blank":
        llm = FakeLlm(["   \n"])
    elif scenario == "validation_failure":
        llm = FakeLlm(["isto não é código de teste"])
    elif scenario == "output_dir_is_file":
        out_dir.write_text("arquivo", encoding="utf-8")
        llm = FakeLlm(
            ["import pytest\nfrom modulo import f\n\ndef test_a():\n    with pytest.raises(ValueError):\n        raise ValueError\n"]
        )
    elif scenario == "output_exists_noninteractive":
        out_dir.mkdir()
        (out_dir / "test_modulo.py").write_text("antigo", encoding="utf-8")

    # Variáveis no processo (load_config lê os.environ quando env=None).
    saved = {name: os.environ.get(name) for name in REQUIRED_VARS}
    for name in REQUIRED_VARS:
        os.environ.pop(name, None)
    os.environ.update(env)

    handler = _LogCapture()
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(
                argv,
                llm_factory=lambda _config: llm,
                stdin=io.StringIO(""),
                stdout=stdout,
                stderr=stderr,
                collector=ok_collector,
            )
        texts += [stdout.getvalue(), stderr.getvalue()]
        # Config e erros de domínio diretamente (mensagens de exceção).
        try:
            config = load_config(env)
            texts += [repr(config), str(config)]
        except AgentError as err:
            texts += [str(err), repr(err)]
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    texts += handler.texts
    return code, texts


@settings(max_examples=100, deadline=None)
@given(key=_keys, scenario=st.sampled_from(SCENARIOS))
def test_api_key_never_appears_in_output(key, scenario):
    """**Validates: Requirements 5.6**"""
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        code, texts = _run_scenario(scenario, key, tmp)

    assert code != 0, f"cenário {scenario} deveria falhar"
    for text in texts:
        assert key not in text, f"chave vazou no cenário {scenario}: {text!r}"


@settings(max_examples=100)
@given(key=_keys)
def test_repr_of_config_hides_key(key):
    """**Validates: Requirements 5.6**"""
    config = load_config(
        {
            "AZURE_OPENAI_API_KEY": key,
            "AZURE_OPENAI_ENDPOINT": "https://x.openai.azure.com/",
            "AZURE_OPENAI_API_VERSION": "2024-06-01",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "dep",
        }
    )
    assert key not in repr(config)
    assert key not in str(config)
