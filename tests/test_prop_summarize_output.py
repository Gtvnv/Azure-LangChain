"""Propriedade 18: o resumo da saída do coletor é limitado."""

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.collection_check import summarize_output

_ALPHABET = st.characters(codec="utf-8", blacklist_categories=("Cs",))
_any_text = st.text(_ALPHABET, max_size=4000)

# Texto com apenas "\n" como separador de linha, para checar o sufixo exato.
_NL_ALPHABET = st.characters(
    codec="utf-8",
    blacklist_categories=("Cs", "Cc", "Zl", "Zp"),
)
_nl_text = st.lists(
    st.text(_NL_ALPHABET, max_size=300), max_size=60
).map("\n".join)
_long_lines_text = st.lists(
    st.text(st.sampled_from(list("ab c")), min_size=50, max_size=400),
    min_size=1,
    max_size=40,
).map("\n".join)


# Feature: pytest-test-generator-agent, Property 18: Collector output summary is bounded
# **Validates: Requirements 3.13**
@settings(max_examples=200, deadline=None)
@given(_any_text)
def test_summary_is_bounded(text):
    result = summarize_output(text)
    assert len(result.splitlines()) <= 20
    assert len(result) <= 2000


# Feature: pytest-test-generator-agent, Property 18: Collector output summary is bounded
# **Validates: Requirements 3.13**
@settings(max_examples=200, deadline=None)
@given(st.one_of(_nl_text, _long_lines_text))
def test_summary_keeps_the_end_of_the_text(text):
    result = summarize_output(text)
    assert text.rstrip().endswith(result)
    assert len(result.splitlines()) <= 20
    assert len(result) <= 2000


# Feature: pytest-test-generator-agent, Property 18: Collector output summary is bounded
# **Validates: Requirements 3.13**
@settings(max_examples=200, deadline=None)
@given(st.one_of(_nl_text, _long_lines_text))
def test_summary_is_idempotent(text):
    once = summarize_output(text)
    # O corte por caracteres pode deixar espaços no início; o strip() inicial
    # da segunda passagem só remove esse espaço em branco, nada mais.
    assert summarize_output(once) == once.strip()
