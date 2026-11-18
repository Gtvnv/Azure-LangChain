"""Testes unitários do writer (Req 4.5-4.10, 4.12)."""

import pytest

from pytest_agent.cli import DEFAULT_OUTPUT_DIR
from pytest_agent.errors import OutputError
from pytest_agent.writer import (
    build_test_file_name,
    check_overwrite,
    resolve_target,
    write_test_file,
)

OLD = "import pytest\n# antigo\n"
NEW = "import pytest\n# novo\n"


def _existing(tmp_path):
    target = tmp_path / "test_mod.py"
    target.write_text(OLD, encoding="utf-8")
    return target


def _ask_returning(answer):
    calls = []

    def ask(prompt):
        calls.append(prompt)
        return answer

    ask.calls = calls
    return ask


def _ask_forbidden(prompt):
    raise AssertionError("não deveria perguntar")


# --- Criação de diretórios e destino ---------------------------------------


def test_resolve_target_uses_output_dir_and_name(tmp_path):
    assert resolve_target(tmp_path / "saida", "mod") == (
        tmp_path / "saida" / build_test_file_name("mod")
    )


def test_write_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "a" / "b" / "c" / "test_mod.py"

    write_test_file(target, NEW)

    assert target.read_text(encoding="utf-8") == NEW


def test_write_in_default_directory_relative_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_OUTPUT_DIR.rstrip("/") == "generated_tests"

    target = resolve_target(DEFAULT_OUTPUT_DIR, "mod")
    write_test_file(target, NEW)

    assert (tmp_path / "generated_tests" / "test_mod.py").read_text(
        encoding="utf-8"
    ) == NEW


def test_write_leaves_no_temp_files(tmp_path):
    target = tmp_path / "out" / "test_mod.py"

    write_test_file(target, NEW)

    assert [p.name for p in target.parent.iterdir()] == ["test_mod.py"]


def test_output_dir_that_is_a_file_raises_output_error(tmp_path):
    blocker = tmp_path / "saida"
    blocker.write_text("sou um arquivo", encoding="utf-8")

    with pytest.raises(OutputError) as excinfo:
        write_test_file(blocker / "test_mod.py", NEW)

    assert str(blocker) in str(excinfo.value)
    assert blocker.read_text(encoding="utf-8") == "sou um arquivo"


# --- Confirmação de sobrescrita ---------------------------------------------


def test_no_existing_file_does_not_ask(tmp_path):
    check_overwrite(tmp_path / "test_mod.py", False, True, _ask_forbidden)


@pytest.mark.parametrize("answer", ["s", "sim", "S", "SIM", " Sim ", "sIm"])
def test_affirmative_answers_allow_overwrite(tmp_path, answer):
    target = _existing(tmp_path)
    ask = _ask_returning(answer)

    check_overwrite(target, False, True, ask)

    assert len(ask.calls) == 1
    assert "[s/N]" in ask.calls[0]
    write_test_file(target, NEW)
    assert target.read_text(encoding="utf-8") == NEW


@pytest.mark.parametrize("answer", ["n", "N", "nao", "não", "", "   ", "y", "ss"])
def test_other_answers_refuse_and_keep_file(tmp_path, answer):
    target = _existing(tmp_path)

    with pytest.raises(OutputError):
        check_overwrite(target, False, True, _ask_returning(answer))

    assert target.read_text(encoding="utf-8") == OLD


def test_eof_on_prompt_refuses_and_keeps_file(tmp_path):
    target = _existing(tmp_path)

    def ask(prompt):
        raise EOFError

    with pytest.raises(OutputError) as excinfo:
        check_overwrite(target, False, True, ask)

    assert "--force" in str(excinfo.value)
    assert target.read_text(encoding="utf-8") == OLD


def test_force_overwrites_without_asking(tmp_path):
    target = _existing(tmp_path)

    check_overwrite(target, True, True, _ask_forbidden)
    check_overwrite(target, True, False, _ask_forbidden)

    write_test_file(target, NEW)
    assert target.read_text(encoding="utf-8") == NEW


def test_non_interactive_refuses_mentions_force_and_keeps_file(tmp_path):
    target = _existing(tmp_path)

    with pytest.raises(OutputError) as excinfo:
        check_overwrite(target, False, False, _ask_forbidden)

    message = str(excinfo.value)
    assert "--force" in message
    assert str(target) in message
    assert target.read_text(encoding="utf-8") == OLD


def test_non_interactive_without_existing_file_is_allowed(tmp_path):
    check_overwrite(tmp_path / "test_mod.py", False, False, _ask_forbidden)
