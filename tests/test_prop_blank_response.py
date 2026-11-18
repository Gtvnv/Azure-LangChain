"""Propriedade 4: respostas em branco do modelo são tratadas como erro."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.errors import LlmError
from pytest_agent.generator import generate_tests
from tests.fakes import FakeLlm, ok_collector

# Feature: pytest-test-generator-agent, Property 4: Blank model responses are treated as errors

_module_names = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,99}", fullmatch=True)

# Respostas vazias ou compostas apenas de espaço em branco (inclui Unicode).
_blank_responses = st.text(
    alphabet=st.sampled_from(list(" \t\n\r\x0b\x0c\u00a0\u2003\u3000")),
    min_size=0,
    max_size=50,
)


@settings(max_examples=100)
@given(response=_blank_responses, module_name=_module_names)
def test_blank_response_is_error_after_one_call(response, module_name):
    """**Validates: Requirements 2.8**"""
    llm = FakeLlm([response])

    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(LlmError) as excinfo:
            generate_tests("def f():\n    return 1\n", module_name, llm, ok_collector)

        assert excinfo.value.category == "vazio"
        assert len(llm.calls) == 1
        assert list(Path(tmp).iterdir()) == []
