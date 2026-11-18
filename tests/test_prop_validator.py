import ast

from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.validator import validate_test_content

_FAILURE_BODIES = {
    "raises": ["with pytest.raises(ValueError):", "    int('x')"],
    "warns": ["with pytest.warns(UserWarning):", "    pass"],
    "fail": ["pytest.fail('falhou')"],
}

_FIRST_LINES = {
    "exact": "import pytest",
    "leading_space": " import pytest",
    "leading_blank": "\nimport pytest",
    "leading_blank_spaces": "  \n\nimport pytest",
}


def _build(first, broken, n_tests, as_class, failure):
    """Monta o conteúdo; retorna (conteúdo, esperado_ok)."""
    body_lines = []
    failure_lines = _FAILURE_BODIES.get(failure, [])

    # A construção de falha vai no primeiro teste, ou em um helper sem prefixo test_.
    if n_tests == 0:
        body_lines += ["def helper():"]
        body_lines += ["    " + ln for ln in (failure_lines or ["pass"])]
    else:
        if as_class:
            body_lines.append("class TestX:")
            indent = "    "
        else:
            indent = ""
        for i in range(n_tests):
            body_lines.append(f"{indent}def test_{i}():")
            inner = failure_lines if i == 0 and failure_lines else ["pass"]
            body_lines += [f"{indent}    {ln}" for ln in inner]
            body_lines.append("")

    content = _FIRST_LINES[first] + "\n" + "\n".join(body_lines) + "\n"
    if broken:
        content += "def (:\n"

    expected = first == "exact" and not broken and n_tests > 0 and failure != "none"
    return content, expected


# Feature: pytest-test-generator-agent, Property 5: Validator accepts content exactly when all conditions hold
# **Validates: Requirements 3.1, 3.2, 3.3, 3.9**
@settings(max_examples=200)
@given(
    first=st.sampled_from(sorted(_FIRST_LINES)),
    broken=st.booleans(),
    n_tests=st.integers(min_value=0, max_value=3),
    as_class=st.booleans(),
    failure=st.sampled_from(["none", "raises", "warns", "fail"]),
)
def test_validator_accepts_exactly_when_all_conditions_hold(first, broken, n_tests, as_class, failure):
    content, expected = _build(first, broken, n_tests, as_class, failure)

    result = validate_test_content(content)

    assert result.ok is expected, (content, result)
    if expected:
        assert result.error is None
        ast.parse(content)
    else:
        assert result.error
