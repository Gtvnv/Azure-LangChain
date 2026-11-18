"""Propriedade 2: entrada em branco é rejeitada antes de qualquer chamada ao LLM."""

import io

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.cli import main
from pytest_agent.errors import InputError
from pytest_agent.input_reader import check_source
from tests.fakes import FakeLlm

_WHITESPACE_CHARS = [chr(c) for c in range(0x110000) if chr(c).isspace()]

# Strings vazias ou formadas apenas por caracteres de espaço em branco.
blank_text = st.text(alphabet=st.sampled_from(_WHITESPACE_CHARS), min_size=0, max_size=50)


# Feature: pytest-test-generator-agent, Property 2: Blank input is rejected before any LLM call
# **Validates: Requirements 1.5**
@settings(max_examples=100)
@given(blank=blank_text)
def test_check_source_rejects_blank(blank):
    with pytest.raises(InputError):
        check_source(blank)


# Feature: pytest-test-generator-agent, Property 2: Blank input is rejected before any LLM call
# **Validates: Requirements 1.5**
@settings(max_examples=100)
@given(blank=blank_text)
def test_cli_rejects_blank_snippet_without_llm_call(blank):
    llm = FakeLlm(["import pytest"])
    out, err = io.StringIO(), io.StringIO()

    code = main(
        ["--snippet", blank, "--module-name", "mod"],
        llm_factory=lambda config: llm,
        stdin=io.StringIO(""),
        stdout=out,
        stderr=err,
    )

    assert code != 0
    assert llm.calls == []
