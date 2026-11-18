"""Verifica se algum nome proibido aparece nos arquivos de texto do repositório.

A lista de nomes proibidos fica fora do repositório. O caminho dela é lido da
variável de ambiente ``FORBIDDEN_NAMES_FILE`` (um nome por linha; linhas em
branco e linhas iniciadas por ``#`` são ignoradas).

Arquivos verificados: os rastreados pelo git e os prontos para commit (novos e
não ignorados). Sem git disponível, percorre o diretório do repositório.
A comparação ignora maiúsculas e minúsculas. O conteúdo e o caminho de cada
arquivo são verificados.

Códigos de saída: 0 sem ocorrências, 1 com ocorrências, 2 erro de uso.
O script nunca imprime o nome encontrado, apenas arquivo e linha.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ENV_VAR = "FORBIDDEN_NAMES_FILE"
REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".hypothesis", "node_modules"}


def load_names(path: Path) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name and not name.startswith("#"):
            names.append(name.casefold())
    return names


def list_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        rels = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return sorted({root / r for r in rels})
    except (OSError, subprocess.CalledProcessError):
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            found.extend(Path(dirpath) / f for f in filenames)
        return sorted(found)


def read_text_or_none(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan(root: Path, names: list[str], ignore: set[Path]) -> list[str]:
    hits = []
    for path in list_files(root):
        if not path.is_file() or path.resolve() in ignore:
            continue
        rel = path.relative_to(root).as_posix()
        if any(n in rel.casefold() for n in names):
            hits.append(f"{rel}: caminho")
        text = read_text_or_none(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            folded = line.casefold()
            if any(n in folded for n in names):
                hits.append(f"{rel}:{number}")
    return hits


def main() -> int:
    raw = os.environ.get(ENV_VAR, "").strip()
    if not raw:
        print(f"Erro: defina a variável de ambiente {ENV_VAR} com o caminho da lista.", file=sys.stderr)
        return 2
    list_path = Path(raw)
    try:
        names = load_names(list_path)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Erro ao ler a lista de nomes proibidos: {type(exc).__name__}.", file=sys.stderr)
        return 2
    if not names:
        print("Erro: a lista de nomes proibidos está vazia.", file=sys.stderr)
        return 2

    hits = scan(REPO_ROOT, names, {list_path.resolve()})
    if hits:
        print("Nomes proibidos encontrados em:", file=sys.stderr)
        for hit in hits:
            print(f"  {hit}", file=sys.stderr)
        return 1
    print("Nenhum nome proibido encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
