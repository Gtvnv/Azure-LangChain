"""Propriedade 17: falhas de coleta alimentam o laço de novas tentativas."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pytest_agent.collection_check import CollectionResult
from pytest_agent.errors import ValidationFailedError
from pytest_agent.generator import MAX_RETRIES, generate_tests
from tests.fakes import FakeLlm

# Feature: pytest-test-generator-agent, Property 17: Collection failures feed the retry loop

_module_names = st.from_regex(r"[a-z_][a-z0-9_]{0,30}", fullmatch=True)
_outcomes = st.lists(st.booleans(), min_size=1, max_size=1 + MAX_RETRIES)


def _valid_content(module_name):
    return (
        "import pytest\n"
        f"from {module_name} import f\n"
        "\n"
        "def test_f():\n"
        "    assert f() == 1\n"
        "\n"
        "def test_f_error():\n"
        "    with pytest.raises(ValueError):\n"
        "        f(None)\n"
    )


class _SequenceCollector:
    """Coletor falso: segue a sequência de resultados e repete o último."""

    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def failure_output(self, index):
        return f"ERRO-COLETA-{index}: ImportError simulado"

    def __call__(self, test_content, module_name, source_code):
        index = min(len(self.calls), len(self.outcomes) - 1)
        self.calls.append((test_content, module_name, source_code))
        if self.outcomes[index]:
            return CollectionResult(True)
        return CollectionResult(False, self.failure_output(len(self.calls) - 1))


@settings(max_examples=100)
@given(outcomes=_outcomes, module_name=_module_names)
def test_collection_failures_feed_retry_loop(outcomes, module_name):
    """**Validates: Requirements 3.7, 3.8, 3.12, 3.13, 9.8**"""
    total = 1 + MAX_RETRIES
    content = _valid_content(module_name)
    llm = FakeLlm([content])
    collector = _SequenceCollector(outcomes)
    source = "def f():\n    return 1\n"

    # Resultado efetivo por tentativa (o último valor se repete).
    effective = [outcomes[min(i, len(outcomes) - 1)] for i in range(total)]
    first_ok = next((i for i, ok in enumerate(effective) if ok), None)

    if first_ok is not None:
        result = generate_tests(source, module_name, llm, collector)

        assert result == content
        assert len(llm.calls) == first_ok + 1
        assert len(collector.calls) == first_ok + 1
        failed_attempts = first_ok
    else:
        with pytest.raises(ValidationFailedError) as excinfo:
            generate_tests(source, module_name, llm, collector)

        assert len(llm.calls) == total
        assert len(collector.calls) == total
        # A última saída de falha aparece na mensagem do erro final.
        assert collector.failure_output(total - 1) in str(excinfo.value)
        failed_attempts = total

    # Cada nova tentativa recebe a saída da falha de coleta anterior.
    for k in range(1, failed_attempts + 1 if first_ok is not None else total):
        if k >= len(llm.calls):
            break
        text = "\n".join(m.content for m in llm.calls[k])
        assert collector.failure_output(k - 1) in text
