"""LLMs falsos para testes offline."""


class FakeLlm:
    """Retorna respostas em sequência, repetindo a última; registra as chamadas."""

    def __init__(self, responses):
        if not responses:
            raise ValueError("responses não pode ser vazio")
        self.responses = list(responses)
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class RaisingFakeLlm:
    """Registra as chamadas e sempre levanta a exceção configurada."""

    def __init__(self, exc):
        self.exc = exc
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        raise self.exc


def ok_collector(test_content, module_name, source_code):
    """Coletor falso que sempre aprova, sem abrir subprocesso."""
    from pytest_agent.collection_check import CollectionResult

    return CollectionResult(True)
