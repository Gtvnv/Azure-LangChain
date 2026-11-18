"""Testes unitários da leitura de entrada (Req 1.2, 1.3, 1.4, 1.6, 1.7, 1.8, 4.3)."""

import io

import pytest

from pytest_agent.errors import InputError
from pytest_agent.input_reader import (
    check_source,
    read_source,
    resolve_module_name,
)


class _TtyStdin(io.StringIO):
    def isatty(self):
        return True


# --- fontes válidas -------------------------------------------------------


def test_read_source_from_file(tmp_path):
    path = tmp_path / "calc.py"
    path.write_bytes("def f():\n    return 'ção'\n".encode("utf-8"))
    code, found = read_source(str(path), None, io.StringIO(""))
    assert code == "def f():\n    return 'ção'\n"
    assert found == path


def test_read_source_from_snippet():
    code, found = read_source(None, "x = 1", io.StringIO(""))
    assert code == "x = 1"
    assert found is None


def test_read_source_from_stdin():
    code, found = read_source(None, None, io.StringIO("def f(): pass\n"))
    assert code == "def f(): pass\n"
    assert found is None


def test_read_source_tty_stdin_is_ignored():
    code, found = read_source(None, None, _TtyStdin("ignorado"))
    assert code == ""
    assert found is None


# --- erros de arquivo -----------------------------------------------------


def test_missing_path_names_path(tmp_path):
    missing = tmp_path / "nao_existe.py"
    with pytest.raises(InputError) as exc:
        read_source(str(missing), None, io.StringIO(""))
    assert str(missing) in str(exc.value)


def test_directory_path_names_path(tmp_path):
    with pytest.raises(InputError) as exc:
        read_source(str(tmp_path), None, io.StringIO(""))
    assert str(tmp_path) in str(exc.value)
    assert "diretório" in str(exc.value)


def test_invalid_utf8_names_path(tmp_path):
    path = tmp_path / "ruim.py"
    path.write_bytes(b"x = '\xff\xfe'\n")
    with pytest.raises(InputError) as exc:
        read_source(str(path), None, io.StringIO(""))
    assert str(path) in str(exc.value)
    assert "UTF-8" in str(exc.value)


# --- sintaxe --------------------------------------------------------------


def test_syntax_error_reports_line_number():
    with pytest.raises(InputError) as exc:
        check_source("x = 1\ny = 2\ndef broken(:\n    pass\n")
    assert "linha 3" in str(exc.value)


def test_valid_source_passes_check():
    check_source("def f():\n    return 1\n")


def test_empty_source_rejected():
    with pytest.raises(InputError):
        check_source("  \n\t")


# --- conflitos de fonte ---------------------------------------------------


def test_file_and_snippet_conflict(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(InputError) as exc:
        read_source(str(path), "y = 2", io.StringIO(""))
    assert "apenas uma fonte" in str(exc.value)


def test_file_and_stdin_conflict(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(InputError) as exc:
        read_source(str(path), None, io.StringIO("y = 2\n"))
    assert "apenas uma fonte" in str(exc.value)


def test_snippet_and_stdin_conflict():
    with pytest.raises(InputError) as exc:
        read_source(None, "x = 1", io.StringIO("y = 2\n"))
    assert "apenas uma fonte" in str(exc.value)


def test_blank_stdin_with_snippet_is_not_a_conflict():
    code, _ = read_source(None, "x = 1", io.StringIO("  \n"))
    assert code == "x = 1"


# --- nome do módulo -------------------------------------------------------


def test_missing_module_name_for_snippet():
    with pytest.raises(InputError) as exc:
        resolve_module_name(None, None)
    assert "obrigatório" in str(exc.value)


def test_module_name_from_snippet_option():
    assert resolve_module_name(None, "meu_mod") == "meu_mod"


def test_module_name_from_file_stem(tmp_path):
    assert resolve_module_name(tmp_path / "calc.py", None) == "calc"


def test_invalid_module_name_rejected():
    with pytest.raises(InputError) as exc:
        resolve_module_name(None, "1abc")
    assert "inválido" in str(exc.value)
