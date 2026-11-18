"""Propriedade 7: o conteúdo gravado é lido de volta de forma idêntica."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.writer import write_test_file

# Texto Unicode (inclui não-ASCII), sem surrogates e sem quebras de linha
# soltas; as quebras são inseridas explicitamente como "\n" ou "\r\n".
_line = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",), blacklist_characters="\r\n"
    ),
    max_size=60,
)
_non_ascii_line = st.sampled_from(["ação", "日本語", "😀 teste", "ñandú", "é"])
_lines = st.lists(st.one_of(_line, _non_ascii_line), max_size=15)
_eol = st.sampled_from(["\n", "\r\n"])


@st.composite
def _contents(draw):
    eol = draw(_eol)
    lines = draw(_lines)
    trailing = draw(st.booleans())
    text = eol.join(lines)
    return text + eol if trailing and lines else text


# Feature: pytest-test-generator-agent, Property 7: Written content reads back identically
# **Validates: Requirements 3.6, 3.10**
@settings(max_examples=100, deadline=None)
@given(content=_contents())
def test_written_content_reads_back_identically(content):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "saida" / "test_modulo.py"

        write_test_file(target, content)

        with open(target, "r", encoding="utf-8", newline="") as handle:
            read_back = handle.read()
        leftovers = [p.name for p in target.parent.iterdir() if p != target]

    assert read_back == content
    assert leftovers == []
