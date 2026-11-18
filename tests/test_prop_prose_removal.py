from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.validator import extract_code, validate_test_content

VALID_CONTENTS = [
    (
        "import pytest\n"
        "from calculadora import add\n"
        "\n"
        "\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n"
        "\n"
        "\n"
        "def test_add_invalid():\n"
        "    with pytest.raises(TypeError):\n"
        "        add(None, 1)\n"
    ),
    (
        "import pytest\r\n"
        "from divisao import divide\r\n"
        "\r\n"
        "def test_divide_zero():\r\n"
        "    with pytest.raises(ValueError):\r\n"
        "        divide(1, 0)\r\n"
    ),
]

# Linhas de prosa em uma única linha física: sem quebras de linha (Cc, Zl, Zp) nem surrogates.
prose_line = (
    st.text(alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zl", "Zp")), max_size=60)
    .filter(lambda s: "```" not in s)
    .filter(lambda s: s.rstrip() != "import pytest")
)


# Feature: pytest-test-generator-agent, Property 6: Prose before the import line is removed
# **Validates: Requirements 3.5**
@settings(max_examples=200)
@given(
    prose=st.lists(prose_line, max_size=8),
    valid=st.sampled_from(VALID_CONTENTS),
    newline=st.sampled_from(["\n", "\r\n"]),
)
def test_prose_before_import_line_is_removed(prose, valid, newline):
    raw = "".join(line + newline for line in prose) + valid

    result = extract_code(raw)

    assert result == valid
    assert validate_test_content(result).ok
