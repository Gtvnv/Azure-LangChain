"""Erros de domínio do Agente. As mensagens já são localizadas (pt-BR)."""


class AgentError(Exception):
    """Erro base do Agente; carrega o código de saída do processo."""

    exit_code: int = 1


class InputError(AgentError):
    """Entrada inválida (arquivo, snippet, stdin, nome de módulo)."""


class ConfigError(AgentError):
    """Configuração ausente ou inválida."""


class LlmError(AgentError):
    """Falha na chamada ao modelo; `category` identifica o tipo."""

    def __init__(self, message: str, category: str = "desconhecido") -> None:
        super().__init__(message)
        self.category = category


class ValidationFailedError(AgentError):
    """O conteúdo gerado não passou na validação após todas as tentativas."""


class OutputError(AgentError):
    """Falha ao gravar ou confirmar a gravação do arquivo de teste."""
