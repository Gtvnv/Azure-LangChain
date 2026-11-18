"""Interface de linha de comando do Agente."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from pytest_agent.collection_check import Collector, collect_with_pytest
from pytest_agent.config import AzureConfig, load_config
from pytest_agent.errors import AgentError
from pytest_agent.generator import generate_tests
from pytest_agent.input_reader import check_source, read_source, resolve_module_name
from pytest_agent.writer import check_overwrite, resolve_target, write_test_file

DEFAULT_OUTPUT_DIR = "generated_tests/"
PROG = "python -m pytest_agent"


_TRANSLATIONS = (
    ("unrecognized arguments:", "argumentos não reconhecidos:"),
    ("expected one argument", "esperava um valor"),
    ("ambiguous option:", "opção ambígua:"),
    ("invalid choice:", "escolha inválida:"),
    ("the following arguments are required:", "os seguintes argumentos são obrigatórios:"),
    ("ignored explicit argument", "argumento explícito ignorado"),
    ("not allowed with argument", "não permitido com o argumento"),
    ("argument ", "argumento "),
)


def _translate(message: str) -> str:
    for en, pt in _TRANSLATIONS:
        message = message.replace(en, pt)
    return message


class PtArgumentParser(argparse.ArgumentParser):
    """ArgumentParser com mensagens de erro em português e código de saída 2."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.out_stream: TextIO | None = None
        self.err_stream: TextIO | None = None
        self._positionals.title = "argumentos posicionais"
        self._optionals.title = "opções"

    def _print_message(self, message: str, file: TextIO | None = None) -> None:
        if not message:
            return
        if file is None or file is sys.stderr:
            file = self.err_stream or sys.stderr
        elif file is sys.stdout:
            file = self.out_stream or sys.stdout
        file.write(message)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "uso:", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "uso:", 1)

    def error(self, message: str) -> None:  # type: ignore[override]
        self._print_message(self.format_usage(), self.err_stream or sys.stderr)
        self.exit(2, f"{self.prog}: erro: {_translate(message)}\n")


def build_parser() -> PtArgumentParser:
    parser = PtArgumentParser(
        prog=PROG,
        description=(
            "Gera testes pytest (test_<nome>.py) para código Python usando "
            "LangChain e Azure OpenAI."
        ),
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument(
        "arquivo",
        nargs="?",
        default=None,
        help="caminho de um arquivo .py com o código a ser testado",
    )
    parser.add_argument(
        "--snippet",
        metavar="TEXTO",
        default=None,
        help="trecho de código Python passado diretamente na linha de comando",
    )
    parser.add_argument(
        "--module-name",
        metavar="NOME",
        default=None,
        help="nome do módulo; obrigatório para snippet ou entrada padrão (stdin)",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=DEFAULT_OUTPUT_DIR,
        help="diretório de saída do arquivo de teste (padrão: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="sobrescreve o arquivo de teste existente sem pedir confirmação",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="mostra esta mensagem de ajuda e sai",
    )
    return parser


def _default_llm_factory(config: AzureConfig) -> Any:
    # Importação tardia: evita carregar LangChain/OpenAI quando não é necessário.
    from pytest_agent.llm_client import AzureLlmClient

    return AzureLlmClient.from_config(config)


def _isatty(stream: Any) -> bool:
    func = getattr(stream, "isatty", None)
    return bool(callable(func) and func())


def _run(
    args: argparse.Namespace,
    parser: PtArgumentParser,
    llm_factory: Callable[[AzureConfig], Any],
    stdin: TextIO,
    stdout: TextIO,
    collector: Collector,
) -> int:
    has_explicit_source = args.arquivo is not None or args.snippet is not None
    if not has_explicit_source and _isatty(stdin):
        parser.error(
            "informe uma fonte de código: um arquivo, --snippet ou entrada padrão (stdin)"
        )

    # Stdin só é lido quando não há arquivo nem --snippet.
    code, path = read_source(
        args.arquivo, args.snippet, None if has_explicit_source else stdin
    )
    check_source(code)
    module_name = resolve_module_name(path, args.module_name)
    config = load_config()

    target = resolve_target(Path(args.output_dir), module_name)

    def ask(prompt: str) -> str:
        stdout.write(prompt)
        stdout.flush()
        line = stdin.readline()
        if line == "":
            raise EOFError
        return line

    # Com código vindo do stdin, o stdin já foi consumido: não há confirmação possível.
    interactive = has_explicit_source and _isatty(stdin)
    check_overwrite(target, args.force, interactive, ask)

    llm = llm_factory(config)
    content = generate_tests(code, module_name, llm, collector)
    write_test_file(target, content)
    stdout.write(f"Arquivo de teste gerado: {target}\n")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    llm_factory: Callable[[AzureConfig], Any] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    collector: Collector = collect_with_pytest,
) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    factory = llm_factory or _default_llm_factory

    parser = build_parser()
    parser.out_stream = stdout
    parser.err_stream = stderr
    try:
        args = parser.parse_args(argv)
        return _run(args, parser, factory, stdin, stdout, collector)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    except AgentError as exc:
        stderr.write(f"Erro: {exc}\n")
        return exc.exit_code
    except KeyboardInterrupt:
        stderr.write("\nOperação interrompida pelo usuário.\n")
        return 130

