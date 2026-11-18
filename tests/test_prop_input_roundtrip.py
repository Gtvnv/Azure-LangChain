"""Propriedade 1: ida e volta de arquivo UTF-8 na leitura da entrada."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.input_reader import read_source

# Texto arbitrário em Unicode, sem surrogates (não codificáveis em UTF-8).
_texts = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=500)


# Feature: pytest-test-generator-agent, Property 1: UTF-8 file input round trip
# **Validates: Requirements 1.1**
@settings(max_examples=100, deadline=None)
@given(text=_texts)
def test_utf8_file_input_round_trip(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "modulo.py"
        path.write_bytes(text.encode("utf-8"))

        code, returned_path = read_source(str(path), None, None)

    assert code == text
    assert returned_path == path
