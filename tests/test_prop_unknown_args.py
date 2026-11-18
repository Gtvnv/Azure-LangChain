"""Propriedade 15: argumentos desconhecidos e abreviações são rejeitados sem chamar o LLM."""
import io
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent import cli
from tests.fakes import FakeLlm

# Feature: pytest-test-generator-agent, Property 15: Unknown arguments and option abbreviations are rejected without an LLM call

_SUPPORTED = ["--snippet", "--module-name", "--output-dir", "--force", "--help"]

_VALID_ARGS = ["--snippet", "def f():\n    return 1\n", "--module-name", "mod"]


def _proper_prefixes(option: str) -> list[str]:
    # Ao menos um caractere após "--" e estritamente menor que o nome completo.
    return [option[:i] for i in range(3, len(option))]


_ABBREVIATIONS = [p for opt in _SUPPORTED for p in _proper_prefixes(opt)]

_long_names = st.from_regex(r"--[A-Za-z][A-Za-z0-9_-]{0,20}", fullmatch=True)
_short_names = st.from_regex(r"-[A-Za-z]", fullmatch=True)
_unknown_options = st.one_of(_long_names, _short_names).filter(
    lambda n: n not in _SUPPORTED and n != "-h"
)
_rejected_options = st.one_of(_unknown_options, st.sampled_from(_ABBREVIATIONS))


@settings(max_examples=100, deadline=None)
@given(
    option=_rejected_options,
    with_value=st.booleans(),
    with_valid_source=st.booleans(),
)
def test_unknown_option_rejected_without_llm_call(option, with_value, with_valid_source):
    """**Validates: Requirements 8.7, 8.8**"""
    llm = FakeLlm(["import pytest"])
    out, err = io.StringIO(), io.StringIO()
    argv = list(_VALID_ARGS) if with_valid_source else []
    argv.append(option)
    if with_value:
        argv.append("valor")

    with tempfile.TemporaryDirectory() as tmp:
        argv += ["--output-dir", tmp]
        code = cli.main(
            argv,
            llm_factory=lambda config: llm,
            stdin=io.StringIO(""),
            stdout=out,
            stderr=err,
        )
        assert list(Path(tmp).iterdir()) == []

    assert code == 2
    assert llm.calls == []
    message = err.getvalue()
    assert "erro" in message
    assert "uso:" in message
    assert "argumentos não reconhecidos" in message
    assert option in message
    assert "usage:" not in message
    assert "unrecognized" not in message


@pytest.mark.parametrize(
    "argv",
    [
        ["--snippet", "x = 1"],
        ["--module-name", "mod"],
        ["--output-dir", "saida"],
        ["--force"],
        ["--help"],
    ],
)
def test_full_option_names_are_accepted(argv):
    """**Validates: Requirements 8.9**"""
    parser = cli.build_parser()
    parser.out_stream, parser.err_stream = io.StringIO(), io.StringIO()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        # Apenas --help encerra o processo, com código 0.
        assert argv == ["--help"]
        assert exc.code == 0
    assert parser.err_stream.getvalue() == ""
