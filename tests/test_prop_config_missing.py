import io
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent import cli
from pytest_agent.config import REQUIRED_VARS, load_config
from pytest_agent.errors import ConfigError
from tests.fakes import FakeLlm

_valid_value = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=20
)
_state = st.sampled_from(["ok", "missing", "empty", "blank"])
_blank_value = st.text(alphabet=" \t", min_size=1, max_size=5)


@st.composite
def _scenarios(draw):
    """Retorna {nome: valor ou None (ausente)} com ao menos uma variável inválida."""
    states = draw(st.lists(_state, min_size=4, max_size=4))
    if all(s == "ok" for s in states):
        idx = draw(st.integers(min_value=0, max_value=3))
        states[idx] = draw(st.sampled_from(["missing", "empty", "blank"]))
    env = {}
    for name, state in zip(REQUIRED_VARS, states):
        if state == "ok":
            env[name] = draw(_valid_value)
        elif state == "missing":
            env[name] = None
        elif state == "empty":
            env[name] = ""
        else:
            env[name] = draw(_blank_value)
    return env


def _invalid(env):
    return [n for n in REQUIRED_VARS if env[n] is None or not env[n].strip()]


# Feature: pytest-test-generator-agent, Property 11: Missing or blank variables are all reported
# **Validates: Requirements 5.4**
@settings(max_examples=100)
@given(env=_scenarios())
def test_missing_or_blank_variables_are_all_reported(env):
    expected = _invalid(env)
    mapping = {k: v for k, v in env.items() if v is not None}

    with pytest.raises(ConfigError) as excinfo:
        load_config(mapping)
    message = str(excinfo.value)
    for name in REQUIRED_VARS:
        assert (name in message) == (name in expected)
    assert ".env.example" in message

    # CLI: zero chamadas ao LLM e status 1.
    llm = FakeLlm(["unused"])
    factory_calls = []

    def factory(config):
        factory_calls.append(config)
        return llm

    with tempfile.TemporaryDirectory() as tmp, pytest.MonkeyPatch.context() as mp:
        mp.chdir(tmp)  # cwd sem .env
        for name, value in env.items():
            if value is None:
                mp.delenv(name, raising=False)
            else:
                mp.setenv(name, value)
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(
            [
                "--snippet",
                "x = 1",
                "--module-name",
                "mod",
                "--output-dir",
                str(Path(tmp) / "out"),
            ],
            llm_factory=factory,
            stdin=io.StringIO(""),
            stdout=out,
            stderr=err,
        )
        assert not (Path(tmp) / "out").exists()

    assert code == 1
    assert llm.calls == []
    assert factory_calls == []
    assert ".env.example" in err.getvalue()
