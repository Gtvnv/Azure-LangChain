"""Testes unitários do comportamento de nova tentativa do orquestrador."""

import pytest

from pytest_agent.errors import ValidationFailedError
from pytest_agent.generator import MAX_RETRIES, generate_tests
from pytest_agent.validator import validate_test_content
from tests.fakes import FakeLlm, ok_collector

SOURCE = "def add(a, b):\n    return a + b\n"

VALID = (
    "import pytest\n"
    "from calc import add\n\n"
    "def test_add():\n"
    "    assert add(1, 2) == 3\n\n"
    "def test_add_falha():\n"
    "    with pytest.raises(TypeError):\n"
    "        add(1, None)\n"
)
INVALID_NO_IMPORT = "def test_x():\n    assert True\n"
INVALID_SYNTAX = "import pytest\ndef test_x(:\n    pass\n"
INVALID_NO_TEST = "import pytest\n\nx = 1\n"


def test_always_invalid_makes_three_calls_and_raises_with_last_error():
    llm = FakeLlm([INVALID_NO_IMPORT, INVALID_SYNTAX, INVALID_NO_TEST])
    last_error = validate_test_content(INVALID_NO_TEST).error

    with pytest.raises(ValidationFailedError) as excinfo:
        generate_tests(SOURCE, "calc", llm, ok_collector)

    assert len(llm.calls) == 1 + MAX_RETRIES == 3
    assert last_error
    assert last_error in str(excinfo.value)
    first_error = validate_test_content(INVALID_NO_IMPORT).error
    assert first_error not in str(excinfo.value)


def test_always_invalid_same_response_makes_exactly_three_calls():
    llm = FakeLlm([INVALID_NO_IMPORT])
    with pytest.raises(ValidationFailedError):
        generate_tests(SOURCE, "calc", llm, ok_collector)
    assert len(llm.calls) == 3


def test_invalid_twice_then_valid_makes_three_calls_and_succeeds():
    llm = FakeLlm([INVALID_NO_IMPORT, INVALID_SYNTAX, VALID])
    result = generate_tests(SOURCE, "calc", llm, ok_collector)
    assert result == VALID
    assert len(llm.calls) == 3


def test_valid_first_makes_one_call():
    llm = FakeLlm([VALID])
    result = generate_tests(SOURCE, "calc", llm, ok_collector)
    assert result == VALID
    assert len(llm.calls) == 1


def test_retry_messages_include_previous_error():
    llm = FakeLlm([INVALID_NO_IMPORT, VALID])
    generate_tests(SOURCE, "calc", llm, ok_collector)
    assert len(llm.calls) == 2
    assert len(llm.calls[1]) > len(llm.calls[0])
    error = validate_test_content(INVALID_NO_IMPORT).error
    assert any(error in m.content for m in llm.calls[1])
