"""Testes unitários da CLI."""
import io
import socket

import pytest

from pytest_agent import cli
from tests.fakes import FakeLlm, ok_collector

VALID_TEST = (
    "import pytest\n"
    "from calc import add\n"
    "\n"
    "def test_add():\n"
    "    assert add(1, 2) == 3\n"
    "\n"
    "def test_add_erro():\n"
    "    with pytest.raises(TypeError):\n"
    "        add(1, None)\n"
)


class TtyStdin(io.StringIO):
    def isatty(self):
        return True


def _run(argv, llm=None, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(
        argv,
        llm_factory=lambda config: llm,
        stdin=stdin if stdin is not None else io.StringIO(""),
        stdout=out,
        stderr=err,
        collector=ok_collector,
    )
    return code, out.getvalue(), err.getvalue()


def test_help_em_portugues_sai_com_zero():
    """Requisitos 8.6"""
    code, out, err = _run(["--help"])
    assert code == 0
    assert "uso:" in out
    assert "usage:" not in out
    assert "--snippet" in out and "--output-dir" in out and "--force" in out
    assert "mostra esta mensagem de ajuda" in out
    assert "gera testes pytest" in out.lower()
    assert err == ""


def test_sem_argumentos_com_terminal_mostra_uso_e_sai_com_erro():
    """Requisitos 8.7"""
    llm = FakeLlm([VALID_TEST])
    code, out, err = _run([], llm=llm, stdin=TtyStdin(""))
    assert code != 0
    assert "uso:" in err
    assert "erro" in err
    assert llm.calls == []


def test_opcao_sem_valor_mostra_uso_e_sai_com_erro():
    """Requisitos 8.7"""
    llm = FakeLlm([VALID_TEST])
    code, out, err = _run(["--snippet"], llm=llm)
    assert code != 0
    assert "uso:" in err
    assert "esperava um valor" in err
    assert llm.calls == []


def test_snippet_sem_module_name_falha_sem_chamar_llm(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    llm = FakeLlm([VALID_TEST])
    code, out, err = _run(["--snippet", "x = 1"], llm=llm)
    assert code != 0
    assert llm.calls == []


def test_sucesso_imprime_caminho_e_sai_com_zero(tmp_path, monkeypatch):
    """Requisitos 4.11"""
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "chave-de-teste-123")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://exemplo.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "deploy")
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "calc.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    out_dir = tmp_path / "saida"
    llm = FakeLlm([VALID_TEST])

    code, out, err = _run([str(source), "--output-dir", str(out_dir)], llm=llm)

    target = out_dir / "test_calc.py"
    assert code == 0, err
    assert str(target) in out
    assert target.read_text(encoding="utf-8") == VALID_TEST
    assert len(llm.calls) == 1


def test_guarda_de_rede_levanta_assertion_error_em_conexao():
    """Requisitos 9.2, 9.7"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(AssertionError, match="acesso à rede não permitido"):
            sock.connect(("127.0.0.1", 9))
    finally:
        sock.close()
    with pytest.raises(AssertionError, match="acesso à rede não permitido"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.parametrize("abreviacao", ["--forc", "--out", "--mod", "--snippe"])
def test_abreviacoes_de_opcoes_sao_rejeitadas_sem_chamar_llm(abreviacao):
    """Requisitos 8.8"""
    llm = FakeLlm([VALID_TEST])
    code, out, err = _run([abreviacao], llm=llm)
    assert code == 2
    assert llm.calls == []


@pytest.mark.parametrize("abreviacao", ["--forc", "--out", "--mod", "--snippe"])
def test_abreviacoes_rejeitadas_nomeiam_o_token(abreviacao):
    """Requisitos 8.8"""
    llm = FakeLlm([VALID_TEST])
    code, out, err = _run([abreviacao], llm=llm)
    assert "uso:" in err
    assert abreviacao in err
    assert llm.calls == []


def test_opcoes_completas_continuam_aceitas(tmp_path, monkeypatch):
    """Requisitos 8.9"""
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "chave-de-teste-123")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://exemplo.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "deploy")
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "saida"
    llm = FakeLlm([VALID_TEST])

    code, out, err = _run(
        [
            "--snippet", "def add(a, b):\n    return a + b\n",
            "--module-name", "calc",
            "--output-dir", str(out_dir),
            "--force",
        ],
        llm=llm,
    )

    assert code == 0, err
    assert (out_dir / "test_calc.py").read_text(encoding="utf-8") == VALID_TEST
    assert len(llm.calls) == 1
