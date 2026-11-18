"""Testes unitários do validador de saída (extract_code e validate_test_content)."""

import pytest

from pytest_agent.validator import ValidationResult, extract_code, validate_test_content

VALID = (
    "import pytest\n"
    "from calc import div\n"
    "\n"
    "def test_ok():\n"
    "    assert div(4, 2) == 2\n"
    "\n"
    "def test_zero():\n"
    "    with pytest.raises(ValueError):\n"
    "        div(1, 0)\n"
)
# Interior de um bloco cercado: a quebra de linha antes da cerca de fechamento é descartada.
INNER = VALID[:-1]


# --- validate_test_content: conteúdo válido -------------------------------


def test_valid_content_passes():
    assert validate_test_content(VALID) == ValidationResult(True, None)


# --- Check 1: primeira linha exatamente `import pytest` -------------------


@pytest.mark.parametrize(
    "prefix",
    ["\n", "  ", "\t", "# comentário\n", "import os\n"],
)
def test_first_line_must_be_import_pytest(prefix):
    result = validate_test_content(prefix + VALID)
    assert not result.ok
    assert "import pytest" in result.error


def test_empty_content_fails_first_check():
    result = validate_test_content("")
    assert not result.ok
    assert "import pytest" in result.error


def test_indented_import_pytest_fails():
    result = validate_test_content(" " + VALID)
    assert not result.ok


def test_crlf_line_endings_pass():
    assert validate_test_content(VALID.replace("\n", "\r\n")).ok


# --- Check 2: ast.parse ---------------------------------------------------


def test_syntax_error_fails_with_line_number():
    content = "import pytest\ndef test_x(:\n    pass\n"
    result = validate_test_content(content)
    assert not result.ok
    assert "sintaxe" in result.error
    assert "2" in result.error


def test_syntax_error_is_reported_before_missing_tests():
    result = validate_test_content("import pytest\nx = (\n")
    assert "sintaxe" in result.error


# --- Check 3: ao menos uma função/método test_* ---------------------------


def test_no_test_function_fails():
    content = "import pytest\n\ndef helper():\n    with pytest.raises(ValueError):\n        pass\n"
    result = validate_test_content(content)
    assert not result.ok
    assert "test_" in result.error


def test_async_test_function_passes():
    content = (
        "import pytest\n\n"
        "async def test_a():\n"
        "    with pytest.raises(ValueError):\n"
        "        raise ValueError\n"
    )
    assert validate_test_content(content).ok


def test_test_method_in_class_passes():
    content = (
        "import pytest\n\n"
        "class TestX:\n"
        "    def test_a(self):\n"
        "        with pytest.raises(ValueError):\n"
        "            raise ValueError\n"
    )
    assert validate_test_content(content).ok


def test_nested_test_function_does_not_count():
    content = (
        "import pytest\n\n"
        "def outer():\n"
        "    def test_inner():\n"
        "        with pytest.raises(ValueError):\n"
        "            raise ValueError\n"
    )
    result = validate_test_content(content)
    assert not result.ok
    assert "test_" in result.error


def test_non_test_method_in_class_fails():
    content = (
        "import pytest\n\n"
        "class TestX:\n"
        "    def helper(self):\n"
        "        with pytest.raises(ValueError):\n"
        "            raise ValueError\n"
    )
    assert not validate_test_content(content).ok


# --- Check 4: ao menos um caso de falha -----------------------------------


def test_missing_failure_case_fails():
    content = "import pytest\n\ndef test_a():\n    assert 1 == 1\n"
    result = validate_test_content(content)
    assert not result.ok
    assert "pytest.raises" in result.error


@pytest.mark.parametrize(
    "body",
    [
        "    with pytest.raises(ValueError):\n        raise ValueError\n",
        "    with pytest.warns(UserWarning):\n        import warnings\n        warnings.warn('x', UserWarning)\n",
        "    pytest.fail('falhou')\n",
    ],
)
def test_each_failure_construct_passes(body):
    content = "import pytest\n\ndef test_a():\n" + body
    assert validate_test_content(content).ok


def test_failure_word_without_pytest_call_fails():
    content = "import pytest\n\ndef test_a():\n    raises = 1\n    assert raises\n"
    assert not validate_test_content(content).ok


# --- Ordem dos checks -----------------------------------------------------


def test_first_failing_check_is_returned():
    # Sem `import pytest` na primeira linha e sem testes: vale o check 1.
    result = validate_test_content("x = 1\n")
    assert "import pytest" in result.error


# --- extract_code ---------------------------------------------------------


def test_extract_plain_code_unchanged():
    assert extract_code(VALID) == VALID


def test_extract_fenced_block_without_tag():
    assert extract_code(f"```\n{VALID}```\n") == INNER


@pytest.mark.parametrize("tag", ["python", "py", "Python3"])
def test_extract_fenced_block_with_language_tag(tag):
    assert extract_code(f"```{tag}\n{VALID}```\n") == INNER


def test_extract_fence_drops_surrounding_prose():
    raw = f"Aqui está:\n```python\n{VALID}```\nEspero que ajude.\n"
    assert extract_code(raw) == INNER


def test_extract_unclosed_fence_takes_rest():
    raw = f"```python\n{VALID}"
    assert extract_code(raw) == VALID


def test_extract_only_first_block_used():
    raw = "```python\nimport pytest\nA = 1\n```\n```python\nimport pytest\nB = 2\n```\n"
    assert extract_code(raw) == "import pytest\nA = 1"


def test_extract_empty_fenced_block_returns_empty():
    assert extract_code("```\n```\n") == ""


def test_extract_trims_prose_before_import_line():
    raw = "Claro! Aqui estão os testes:\n\n" + VALID
    assert extract_code(raw) == VALID


def test_extract_without_import_pytest_returns_text_unchanged():
    raw = "def test_a():\n    pass\n"
    assert extract_code(raw) == raw


def test_extract_without_import_pytest_line_fails_validation():
    raw = "Texto qualquer\ndef test_a():\n    pass\n"
    cleaned = extract_code(raw)
    assert cleaned == raw
    assert not validate_test_content(cleaned).ok


def test_extract_fence_then_trim_prose_inside_block():
    raw = f"```python\nComentário solto\n{VALID}```"
    assert extract_code(raw) == INNER


def test_extract_import_line_with_trailing_whitespace_is_found():
    raw = "prosa\nimport pytest   \nx = 1\n"
    assert extract_code(raw).startswith("import pytest")


def test_extract_is_idempotent_on_fenced_input():
    raw = f"texto\n```python\n{VALID}```\n"
    once = extract_code(raw)
    assert extract_code(once) == once


def test_extracted_fenced_output_validates():
    assert validate_test_content(extract_code(f"```python\n{VALID}```")).ok
