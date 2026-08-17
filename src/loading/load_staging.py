"""Carga em staging (RF05 da spec), com idempotência via UPSERT (RF07).

Cada função recebe registros JÁ VALIDADOS por `src/quality/*` — este módulo
não valida dados, apenas persiste. Reprocessar o mesmo `batch_date` para a
mesma chave natural atualiza a linha existente em vez de duplicá-la, porque a
chave primária das tabelas de staging é a chave natural da entidade (ver
`staging_schema.py`).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date

from pydantic import BaseModel
from sqlalchemy import Table, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.loading.staging_schema import (
    STAGING_SCHEMA,
    metadata,
    stg_customers,
    stg_order_items,
    stg_order_payments,
    stg_order_reviews,
    stg_orders,
    stg_products,
    stg_sellers,
)
from src.models.schemas import (
    CustomerRecord,
    OrderItemRecord,
    OrderRecord,
    PaymentRecord,
    ProductRecord,
    ReviewRecord,
    SellerRecord,
)

logger = logging.getLogger(__name__)


def create_staging_schema(engine: Engine) -> None:
    """Cria o schema `staging` e todas as tabelas, se ainda não existirem.

    Idempotente: seguro chamar em toda execução do pipeline (RF07).

    Usa SQL bruto (`CREATE SCHEMA IF NOT EXISTS`) em vez de
    `CreateSchema(if_not_exists=True)` do SQLAlchemy: esse parâmetro é da API
    2.0 e é SILENCIOSAMENTE IGNORADO no SQLAlchemy 1.4 (a versão que o
    Airflow 2.9 fixa como dependência) — o schema seria recriado sem a
    cláusula IF NOT EXISTS, quebrando com "schema already exists" em toda
    execução após a primeira. Bug real, encontrado rodando a DAG de verdade
    contra Airflow (ver docs/adr/, ADR sobre a tensão de versão SQLAlchemy).
    """
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {STAGING_SCHEMA}"))
    metadata.create_all(engine, checkfirst=True)
    logger.info("staging_schema_pronto", extra={"schema": STAGING_SCHEMA})


def _upsert_records(
    engine: Engine,
    table: Table,
    records: Sequence[BaseModel],
    batch_date: date,
) -> int:
    """UPSERT genérico: insere registros novos, atualiza os já existentes.

    A chave de conflito é a chave primária da tabela (chave natural da
    entidade) — não uma chave técnica separada, deliberadamente, para que
    reprocessar o mesmo registro em outro `batch_date` apenas atualize
    `batch_date`/`loaded_at` e os demais campos, em vez de criar duplicata.
    """
    if not records:
        logger.info(
            "nenhum_registro_para_carregar",
            extra={"tabela": table.name, "batch_date": str(batch_date)},
        )
        return 0

    linhas = [
        {**registro.model_dump(), "batch_date": batch_date} for registro in records
    ]

    colunas_pk = {coluna.name for coluna in table.primary_key}
    colunas_atualizaveis = [
        coluna.name for coluna in table.columns if coluna.name not in colunas_pk
    ]

    stmt = pg_insert(table).values(linhas)
    stmt = stmt.on_conflict_do_update(
        index_elements=list(colunas_pk),
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info(
        "registros_carregados_em_staging",
        extra={
            "tabela": table.name,
            "batch_date": str(batch_date),
            "linhas": len(linhas),
        },
    )
    return len(linhas)


def load_orders_staging(
    engine: Engine, records: Sequence[OrderRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `orders` em `staging.stg_orders`."""
    return _upsert_records(engine, stg_orders, records, batch_date)


def load_customers_staging(
    engine: Engine, records: Sequence[CustomerRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `customers` em `staging.stg_customers`."""
    return _upsert_records(engine, stg_customers, records, batch_date)


def load_order_items_staging(
    engine: Engine, records: Sequence[OrderItemRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `order_items` em `staging.stg_order_items`."""
    return _upsert_records(engine, stg_order_items, records, batch_date)


def load_products_staging(
    engine: Engine, records: Sequence[ProductRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `products` em `staging.stg_products`."""
    return _upsert_records(engine, stg_products, records, batch_date)


def load_sellers_staging(
    engine: Engine, records: Sequence[SellerRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `sellers` em `staging.stg_sellers`."""
    return _upsert_records(engine, stg_sellers, records, batch_date)


def load_payments_staging(
    engine: Engine, records: Sequence[PaymentRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `order_payments` em `staging.stg_order_payments`."""
    return _upsert_records(engine, stg_order_payments, records, batch_date)


def load_reviews_staging(
    engine: Engine, records: Sequence[ReviewRecord], batch_date: date
) -> int:
    """Carrega registros válidos de `order_reviews` em `staging.stg_order_reviews`."""
    return _upsert_records(engine, stg_order_reviews, records, batch_date)
