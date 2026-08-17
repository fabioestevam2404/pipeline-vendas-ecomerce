"""Fixtures de testes de integração.

Requer um PostgreSQL acessível via as mesmas variáveis de ambiente usadas em
produção (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST,
POSTGRES_PORT) — ver `.env.example` e `.github/workflows/ci.yml`, que sobe um
serviço de banco com essas credenciais para rodar exatamente estes testes.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from src.config import Settings
from src.db import get_engine
from src.loading.load_mart import create_mart_schema
from src.loading.load_staging import create_staging_schema
from src.loading.mart_schema import MART_SCHEMA
from src.loading.staging_schema import STAGING_SCHEMA


def _test_settings() -> Settings:
    return Settings(
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        raw_data_dir=Path("/tmp/unused"),  # não usado nestes testes
        landing_zone_dir=Path("/tmp/unused"),  # não usado nestes testes
        quarantine_dir=Path("/tmp/unused"),  # não usado nestes testes
    )


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Engine conectada a um PostgreSQL real, com schema `staging` limpo.

    O schema é recriado a cada teste (drop + create) para garantir isolamento
    entre testes, sem depender de rollback de transação — a carga real usa
    `engine.begin()` internamente, então cada UPSERT já é commitado.
    """
    settings = _test_settings()
    eng = get_engine(settings)

    with eng.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {STAGING_SCHEMA} CASCADE"))

    create_staging_schema(eng)

    yield eng

    with eng.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {STAGING_SCHEMA} CASCADE"))

    eng.dispose()


@pytest.fixture
def mart_engine() -> Iterator[Engine]:
    """Engine conectada a um PostgreSQL real, com schema `mart` limpo.

    Fixture separada de `engine` (staging) porque os testes de mart não
    precisam do schema de staging, e vice-versa — mantém os testes rápidos e
    sem dependência cruzada.
    """
    settings = _test_settings()
    eng = get_engine(settings)

    with eng.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {MART_SCHEMA} CASCADE"))

    create_mart_schema(eng)

    yield eng

    with eng.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {MART_SCHEMA} CASCADE"))

    eng.dispose()
