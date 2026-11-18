"""Propriedade 9: validação do nome do módulo segue a regra de identificador."""

import io
import re
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.cli import main
from pytest_agent.input_reader import is_valid_module_name
from tests.fakes import FakeLlm

_RULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,99}")
_ALPHABET = st.characters(
    codec="utf-8", blacklist_categories=("Cs",), blacklist_characters="\x00"
)
_ASCII_ID_CHARS = st.sampled_from(
    list("abcxyzABCXYZ0123456789_")
)

_valid_names = st.builds(
    lambda first, rest: first + rest,
    st.sampled_from(list("abcxyzABCXYZ_")),
    st.text(_ASCII_ID_CHARS, max_size=99),
)

_invalid_names = st.one_of(
    st.text(_ALPHABET, max_size=150).filter(lambda s: _RULE.fullmatch(s) is None),
    st.text(_ASCII_ID_CHARS, min_size=101, max_size=130),
    st.builds(lambda d, r: d + r, st.sampled_from(list("0123456789")), st.text(_ASCII_ID_CHARS, max_size=20)),
    st.builds(lambda s: s + "\n", st.text(_ASCII_ID_CHARS, min_size=1, max_size=20)),
    st.builds(lambda s: s + "é", st.text(_ASCII_ID_CHARS, max_size=20)),
)

SNIPPET = "def f():\n    return 1\n"
VALID_TEST = "import pytest\n\n\ndef test_f():\n    with pytest.raises(ValueError):\n        raise ValueError()\n"


# Feature: pytest-test-generator-agent, Property 9: Module name validation matches the identifier rule
# **Validates: Requirements 4.4**
@settings(max_examples=200, deadline=None)
@given(st.text(_ALPHABET, max_size=150))
def test_is_valid_module_name_matches_rule(name):
    assert is_valid_module_name(name) == (_RULE.fullmatch(name) is not None)


# Feature: pytest-test-generator-agent, Property 9: Module name validation matches the identifier rule
# **Validates: Requirements 4.4**
@settings(max_examples=200, deadline=None)
@given(_valid_names)
def test_generated_valid_names_accepted(name):
    assert is_valid_module_name(name)


# Feature: pytest-test-generator-agent, Property 9: Module name validation matches the identifier rule
# **Validates: Requirements 4.4**
@settings(max_examples=200, deadline=None)
@given(_invalid_names)
def test_generated_invalid_names_rejected(name):
    assert not is_valid_module_name(name)


# Feature: pytest-test-generator-agent, Property 9: Module name validation matches the identifier rule
# **Validates: Requirements 4.4**
@settings(max_examples=100, deadline=None)
@given(_invalid_names)
def test_cli_invalid_module_name_creates_no_file(name):
    llm = FakeLlm([VALID_TEST])
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "saida"
        code = main(
            [
                "--snippet",
                SNIPPET,
                f"--module-name={name}",
                "--output-dir",
                str(out_dir),
            ],
            llm_factory=lambda config: llm,
            stdin=io.StringIO(""),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
        assert code != 0
        assert not out_dir.exists() or not any(out_dir.iterdir())
        assert list(Path(tmp).rglob("*.py")) == []
    assert llm.calls == []
