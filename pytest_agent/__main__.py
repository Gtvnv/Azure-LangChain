"""Permite executar o Agente com ``python -m pytest_agent``."""

import sys

from pytest_agent.cli import main

if __name__ == "__main__":
    sys.exit(main())
