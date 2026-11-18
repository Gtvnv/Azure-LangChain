"""Verificações da estrutura do repositório (arquivos, README, pacote)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENV_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _public_functions(path: Path) -> list[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    ]


# --- requirements.txt (8.1) -------------------------------------------------


def test_requirements_lists_required_packages_one_per_line():
    lines = [ln.strip() for ln in _read("requirements.txt").splitlines() if ln.strip()]
    pattern = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)>=(\d[^,\s]*),<(\d+)$")
    names: list[str] = []
    for line in lines:
        match = pattern.fullmatch(line)
        assert match, f"linha inválida em requirements.txt: {line!r}"
        names.append(match.group(1).lower())
    required = ["langchain", "langchain-openai", "python-dotenv", "pytest", "hypothesis"]
    assert len(names) == len(set(names)), f"pacotes duplicados: {names}"
    assert sorted(names) == sorted(required)


# --- .gitignore (5.7) -------------------------------------------------------


def test_gitignore_has_required_patterns():
    lines = {ln.strip() for ln in _read(".gitignore").splitlines()}
    assert ".env" in lines
    assert any(p in lines for p in (".venv/", "venv/", ".venv", "venv"))
    assert any(p in lines for p in ("__pycache__/", "__pycache__"))
    assert any(p in lines for p in (".pytest_cache/", ".pytest_cache"))


def test_gitignore_anchors_generated_tests_to_root():
    lines = {ln.strip() for ln in _read(".gitignore").splitlines()}
    assert "/generated_tests/" in lines
    assert "generated_tests/" not in lines, "padrão sem âncora ignoraria examples/generated_tests/"


# --- .env.example (5.5) -----------------------------------------------------


def test_env_example_has_four_vars_with_placeholders_and_comments():
    lines = _read(".env.example").splitlines()
    values: dict[str, str] = {}
    for i, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, sep, value = line.partition("=")
        assert sep == "=", f"linha inválida: {line!r}"
        values[name.strip()] = value.strip()
        previous = lines[i - 1].strip() if i > 0 else ""
        assert previous.startswith("#") and len(previous) > 2, f"{name} sem comentário"
    assert tuple(values) == ENV_VARS
    assert all(values.values()), "valor de exemplo vazio"
    assert values["AZURE_OPENAI_API_KEY"] in {"sua-chave-aqui"}
    assert re.fullmatch(r"[0-9a-fA-F]{32}", values["AZURE_OPENAI_API_KEY"]) is None


# --- pyproject.toml (6.5) ---------------------------------------------------


def test_pyproject_configures_pytest_paths():
    data = tomllib.loads(_read("pyproject.toml"))
    opts = data["tool"]["pytest"]["ini_options"]
    assert "examples" in opts["pythonpath"]
    assert "." in opts["pythonpath"]
    assert {"tests", "examples"} <= set(opts["testpaths"])


# --- exemplos (6.1, 6.2, 6.3) -----------------------------------------------

EXAMPLE_MODULES = sorted(
    p for p in (ROOT / "examples").glob("*.py") if not p.name.startswith("_")
)


def test_examples_have_enough_modules_and_functions():
    assert len(EXAMPLE_MODULES) >= 2
    total = 0
    for module in EXAMPLE_MODULES:
        funcs = _public_functions(module)
        assert funcs, f"{module.name} sem funções"
        for fn in funcs:
            assert fn.returns is not None and all(
                a.annotation is not None for a in fn.args.args
            ), f"{fn.name} sem assinatura documentada"
            assert ast.get_docstring(fn), f"{fn.name} sem docstring"
        total += len(funcs)
    assert total >= 3


def test_divide_raises_value_error():
    sys.path.insert(0, str(ROOT / "examples"))
    try:
        from divisao import divide
    finally:
        sys.path.remove(str(ROOT / "examples"))
    with pytest.raises(ValueError):
        divide(1, 0)


@pytest.mark.parametrize("module", EXAMPLE_MODULES, ids=lambda p: p.name)
def test_example_test_file_covers_every_function(module: Path):
    test_file = ROOT / "examples" / "generated_tests" / f"test_{module.stem}.py"
    assert test_file.is_file()
    assert len(list((ROOT / "examples" / "generated_tests").glob(f"test_{module.stem}.py"))) == 1
    tree = ast.parse(test_file.read_text(encoding="utf-8"))
    test_names = [
        n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    for fn in _public_functions(module):
        assert any(fn.name in t for t in test_names), f"nenhum teste para {fn.name}"


def test_divide_example_test_asserts_value_error():
    content = _read("examples/generated_tests/test_divisao.py")
    assert "pytest.raises(ValueError" in content


def test_every_example_test_file_uses_pytest_raises():
    for test_file in (ROOT / "examples" / "generated_tests").glob("test_*.py"):
        text = test_file.read_text(encoding="utf-8")
        if "def divide" in _read(f"examples/{test_file.name[5:]}"):
            assert "pytest.raises" in text


# --- README (6.6, 7.2 a 7.7) ------------------------------------------------

README_HEADINGS = (
    "Descrição do projeto",
    "Funcionalidades",
    "Visão geral da arquitetura",
    "Pré-requisitos",
    "Instalação",
    "Configuração das variáveis de ambiente",
    "Como executar o Agente",
    "Exemplos de uso",
    "Como rodar os testes com pytest",
    "Estrutura do projeto",
    "Notas de segurança",
    "Licença",
)


def _readme_sections() -> dict[str, str]:
    text = _read("README.md")
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def test_readme_has_the_twelve_headings():
    sections = _readme_sections()
    for heading in README_HEADINGS:
        assert heading in sections, f"seção ausente: {heading}"


def test_readme_installation_steps_in_order_for_both_shells():
    section = _readme_sections()["Instalação"]
    steps = re.findall(r"^\d+\. ", section, flags=re.MULTILINE)
    assert len(steps) >= 4
    expected = [
        ("python -m venv .venv", "python3 -m venv .venv"),
        (r".\.venv\Scripts\Activate.ps1", "source .venv/bin/activate"),
        ("pip install -r requirements.txt", "pip install -r requirements.txt"),
        ("Copy-Item .env.example .env", "cp .env.example .env"),
    ]
    pos_ps = pos_sh = -1
    for ps_cmd, sh_cmd in expected:
        new_ps = section.find(ps_cmd, pos_ps + 1)
        new_sh = section.find(sh_cmd, pos_sh + 1)
        assert new_ps > pos_ps, f"comando PowerShell fora de ordem/ausente: {ps_cmd}"
        assert new_sh > pos_sh, f"comando bash fora de ordem/ausente: {sh_cmd}"
        pos_ps, pos_sh = new_ps, new_sh
    assert "PowerShell" in section and "bash" in section


def test_readme_variable_table_lists_every_env_variable():
    section = _readme_sections()["Configuração das variáveis de ambiente"]
    rows = [ln for ln in section.splitlines() if ln.startswith("|")]
    for name in ENV_VARS:
        row = next((r for r in rows if f"`{name}`" in r), None)
        assert row is not None, f"{name} fora da tabela"
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) >= 3 and all(cells), f"linha incompleta para {name}"


def test_readme_shows_generation_command_for_each_example():
    text = _read("README.md")
    for module in EXAMPLE_MODULES:
        cmd = f"python -m pytest_agent examples/{module.name} --output-dir examples/generated_tests"
        assert cmd in text


def test_readme_safety_notes():
    section = _readme_sections()["Notas de segurança"]
    lowered = section.lower()
    assert "nunca" in lowered and "`.env`" in section and ".gitignore" in section
    assert "segredo" in lowered
    assert "llm" in lowered and "revise" in lowered
    assert "incorretos" in lowered or "incorreto" in lowered


def test_readme_image_links_point_to_existing_files_with_alt_text():
    text = _read("README.md")
    for alt, target in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)", text):
        assert alt.strip(), f"imagem sem texto alternativo: {target}"
        assert target.startswith("images/"), target
        assert (ROOT / target).is_file(), f"imagem inexistente: {target}"


# --- pacote pytest_agent (8.3, 8.4, 8.5) ------------------------------------


def test_package_contains_no_example_files():
    package = ROOT / "pytest_agent"
    names = {p.name for p in package.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert not names & {"calculadora.py", "divisao.py"}
    assert not any(n.startswith("test_") for n in names)
    assert not any("generated_tests" in p.parts for p in package.rglob("*"))


# Independência dos módulos centrais (8.5). Dependências reais do código:
# config -> errors; prompt -> nenhuma; validator -> nenhuma;
# llm_client -> config, prompt, errors (usa AzureConfig, Message e LlmError).
# Nenhum deles pode importar cli, generator, writer ou input_reader, ou seja,
# cada um pode ser importado e testado sem acionar o gerador ou a CLI.
# Entre os quatro, só llm_client depende dos outros (config e prompt, por tipos).
ALLOWED_INTERNAL = {
    "config": {"errors"},
    "prompt": set(),
    "validator": set(),
    "llm_client": {"config", "prompt", "errors"},
}


@pytest.mark.parametrize("module", sorted(ALLOWED_INTERNAL))
def test_core_module_imports_in_fresh_process_without_orchestration(module: str):
    code = (
        "import json, sys\n"
        f"import pytest_agent.{module}\n"
        "loaded = sorted(m.split('.')[1] for m in sys.modules "
        "if m.startswith('pytest_agent.') and m.count('.') == 1)\n"
        "print(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    loaded = set(json.loads(result.stdout.strip().splitlines()[-1]))
    assert loaded <= {module} | ALLOWED_INTERNAL[module], f"carregou {loaded}"
    others = {"config", "prompt", "llm_client", "validator"} - {module}
    unexpected = (loaded & others) - ALLOWED_INTERNAL[module]
    assert not unexpected


def test_module_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "pytest_agent", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "--snippet" in result.stdout


# --- workflow de CI (10.1, 10.3, 10.4, 10.6, 10.7, 10.8) --------------------

WORKFLOW = Path(".github") / "workflows" / "ci.yml"


def test_ci_workflow_exists():
    assert (ROOT / WORKFLOW).is_file()


@pytest.mark.parametrize(
    "snippet",
    [
        "python -m pytest",
        "pip install -r requirements.txt",
        "contents: read",
        "FORBIDDEN_NAMES",
        "if: ${{ env.FORBIDDEN_NAMES != '' }}",
        "FORBIDDEN_NAMES_FILE",
    ],
)
def test_ci_workflow_contains_required_text(snippet: str):
    assert snippet in _read(WORKFLOW.as_posix())


def test_ci_workflow_does_not_reference_azure_openai():
    assert "AZURE_OPENAI" not in _read(WORKFLOW.as_posix())
