"""Propriedade 3: o prompt carrega o código-fonte e o nome do módulo."""

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.prompt import build_messages

# Feature: pytest-test-generator-agent, Property 3: Prompt carries the source and module name

_module_names = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,99}", fullmatch=True)

# Código arbitrário, incluindo chaves, quebras de linha e caracteres não ASCII.
_source_code = st.text(
    alphabet=st.one_of(
        st.sampled_from(list(string.printable)),
        st.sampled_from(list("{}%çãéü€😀")),
    ),
    min_size=0,
    max_size=500,
)


@settings(max_examples=200)
@given(source_code=_source_code, module_name=_module_names)
def test_prompt_carries_source_and_module_name(source_code, module_name):
    """**Validates: Requirements 2.1, 2.4**"""
    messages = build_messages(source_code, module_name)

    user_contents = [m.content for m in messages if m.role == "user"]
    assert user_contents, "nenhuma mensagem de usuário"
    user_text = "\n".join(user_contents)

    # Código-fonte literal e nome do módulo presentes no prompt.
    assert source_code in user_text
    assert module_name in user_text
    assert f"from {module_name} import" in user_text
