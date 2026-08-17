"""Criação da engine de conexão com o PostgreSQL.

Módulo isolado (não em src/config.py) porque a criação da engine é a única
parte do projeto que efetivamente abre uma conexão de rede — mantê-la
separada facilita mockar/isolar em testes que não precisam de banco.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import Settings


def get_engine(settings: Settings) -> Engine:
    """Cria a engine de conexão com o PostgreSQL a partir das configurações.

    Nunca logar `settings.postgres_dsn` diretamente — contém a senha em texto
    plano (ver docs/ai/security-rules.md).
    """
    return create_engine(settings.postgres_dsn, pool_pre_ping=True)
