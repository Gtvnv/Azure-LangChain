"""Propriedade 13: envolver código em cerca Markdown e extrair devolve o original."""

import ast

from hypothesis import given, settings, strategies as st

from pytest_agent.validator import extract_code

_identifier = st.from_regex(r"[a-z][a-z0-9_]{0,10}", fullmatch=True)
_int_literal = st.integers(min_value=-1000, max_value=1000)
_text_literal = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Cc", "Zl", "Zp"),
        blacklist_characters="\\'\"`",
    ),
    max_size=15,
)


@st.composite
def _statement(draw):
    name = draw(_identifier)
    kind = draw(st.sampled_from(["assign_int", "assign_str", "comment", "blank", "raises"]))
    if kind == "assign_int":
        return f"v_{name} = {draw(_int_literal)}"
    if kind == "assign_str":
        return f"v_{name} = '{draw(_text_literal)}'"
    if kind == "comment":
        return f"# {draw(_text_literal)}"
    if kind == "blank":
        return ""
    return f"def test_{name}():\n    with pytest.raises(ValueError):\n        raise ValueError('x')"


@st.composite
def _valid_code(draw):
    statements = draw(st.lists(_statement(), max_size=8))
    code = "\n".join(["import pytest", *statements])
    if draw(st.booleans()):
        code += "\n"
    ast.parse(code)
    return code


_language_tag = st.one_of(st.just(""), st.from_regex(r"[a-z][a-z0-9+-]{0,9}", fullmatch=True))


# Feature: pytest-test-generator-agent, Property 13: Fence wrapping round trip
# **Validates: Requirements 3.4, 9.4**
@settings(max_examples=200)
@given(code=_valid_code(), tag=_language_tag)
def test_fence_wrapping_round_trip(code, tag):
    wrapped = f"```{tag}\n{code}\n```"
    assert extract_code(wrapped) == code


# Feature: pytest-test-generator-agent, Property 13: Fence wrapping round trip
# **Validates: Requirements 3.4, 9.4**
@settings(max_examples=200)
@given(code=_valid_code(), tag=_language_tag)
def test_fence_wrapping_round_trip_with_surrounding_prose(code, tag):
    wrapped = f"Aqui está o código:\n```{tag}\n{code}\n```\nEspero ter ajudado."
    assert extract_code(wrapped) == code
