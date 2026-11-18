from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.input_reader import resolve_module_name
from pytest_agent.writer import build_test_file_name, resolve_target

valid_names = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,99}", fullmatch=True)


# Feature: pytest-test-generator-agent, Property 8: Test file naming
# **Validates: Requirements 4.1, 4.2**
@settings(max_examples=100)
@given(name=valid_names)
def test_test_file_name_from_file_stem_and_module_name(name):
    expected = f"test_{name}.py"

    assert build_test_file_name(name) == expected

    # Origem: stem do arquivo de entrada (Req 4.1)
    from_file = resolve_module_name(Path("algum_dir") / f"{name}.py", None)
    assert from_file == name
    assert build_test_file_name(from_file) == expected

    # Origem: --module-name (Req 4.2)
    from_option = resolve_module_name(None, name)
    assert from_option == name
    assert build_test_file_name(from_option) == expected

    assert resolve_target(Path("saida"), from_option) == Path("saida") / expected
