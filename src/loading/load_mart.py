"""Carga do data mart (schema `mart`) — dimensões e fato_pedidos.

Estratégia de chaves substitutas (surrogate keys):
- `dim_customers.customer_sk`: gerada pelo banco (IDENTITY), preservada em
  upserts subsequentes (o UPSERT nunca toca a coluna `customer_sk`).
- `dim_tempo.date_sk`: já é determinística (AAAAMMDD), não precisa de IDENTITY.
- `fact_pedidos`: resolve `customer_sk`/`date_sk` LENDO as dimensões já
  persistidas no banco — não reaproveita as chaves calculadas em memória por
  `build_dim_customers`/`build_dim_tempo` (que só existem para permitir testar
  essas transformações isoladamente, sem depender de banco).
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.loading.fact_pedidos import build_fact_pedidos
from src.loading.mart_schema import (
    MART_SCHEMA,
    dim_customers,
    dim_pagamento,
    dim_products,
    dim_sellers,
    dim_tempo,
    fact_pedidos,
    metadata,
)

logger = logging.getLogger(__name__)


def create_mart_schema(engine: Engine) -> None:
    """Cria o schema `mart` e todas as tabelas, se ainda não existirem.

    A ordem de criação (dimensões antes do fato) é resolvida automaticamente
    pelo SQLAlchemy a partir das `ForeignKeyConstraint` declaradas em
    `mart_schema.py`.

    Usa SQL bruto em vez de `CreateSchema(if_not_exists=True)` — ver
    docstring de `create_staging_schema` em `load_staging.py` para o porquê
    (parâmetro ignorado silenciosamente sob SQLAlchemy 1.4/Airflow).
    """
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {MART_SCHEMA}"))
    metadata.create_all(engine, checkfirst=True)
    logger.info("mart_schema_pronto", extra={"schema": MART_SCHEMA})


def load_dim_customers_mart(engine: Engine, dim_customers_df: pd.DataFrame) -> int:
    """Persiste dim_customers, preservando customer_sk já existentes.

    `dim_customers_df` é a saída de `build_dim_customers` (inclui uma
    `customer_sk` calculada em memória) — essa coluna é descartada aqui de
    propósito: a sk de verdade vem do banco (IDENTITY), estável entre execuções.
    """
    if dim_customers_df.empty:
        logger.info("dim_customers_sem_registros_para_carregar")
        return 0

    colunas_a_persistir = [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ]
    linhas = dim_customers_df[colunas_a_persistir].to_dict("records")

    stmt = pg_insert(dim_customers).values(linhas)
    colunas_atualizaveis = [c for c in colunas_a_persistir if c != "customer_id"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("dim_customers_carregada", extra={"linhas": len(linhas)})
    return len(linhas)


def load_dim_tempo_mart(engine: Engine, dim_tempo_df: pd.DataFrame) -> int:
    """Persiste dim_tempo. `date_sk` é determinística — datas já carregadas
    não mudam, então usamos ON CONFLICT DO NOTHING em vez de UPDATE."""
    if dim_tempo_df.empty:
        logger.info("dim_tempo_sem_registros_para_carregar")
        return 0

    linhas = dim_tempo_df.to_dict("records")
    stmt = pg_insert(dim_tempo).values(linhas)
    stmt = stmt.on_conflict_do_nothing(index_elements=["date_sk"])

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("dim_tempo_carregada", extra={"linhas": len(linhas)})
    return len(linhas)


def load_dim_products_mart(engine: Engine, dim_products_df: pd.DataFrame) -> int:
    """Persiste dim_products, preservando product_sk já existentes (mesmo
    padrão de `load_dim_customers_mart`: sk real vem do banco via IDENTITY)."""
    if dim_products_df.empty:
        logger.info("dim_products_sem_registros_para_carregar")
        return 0

    colunas_a_persistir = [
        "product_id",
        "product_category_name",
        "product_category_name_english",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
    linhas = dim_products_df[colunas_a_persistir].to_dict("records")

    stmt = pg_insert(dim_products).values(linhas)
    colunas_atualizaveis = [c for c in colunas_a_persistir if c != "product_id"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["product_id"],
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("dim_products_carregada", extra={"linhas": len(linhas)})
    return len(linhas)


def load_dim_sellers_mart(engine: Engine, dim_sellers_df: pd.DataFrame) -> int:
    """Persiste dim_sellers, preservando seller_sk já existentes (mesmo
    padrão de `load_dim_customers_mart`: sk real vem do banco via IDENTITY)."""
    if dim_sellers_df.empty:
        logger.info("dim_sellers_sem_registros_para_carregar")
        return 0

    colunas_a_persistir = [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ]
    linhas = dim_sellers_df[colunas_a_persistir].to_dict("records")

    stmt = pg_insert(dim_sellers).values(linhas)
    colunas_atualizaveis = [c for c in colunas_a_persistir if c != "seller_id"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["seller_id"],
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("dim_sellers_carregada", extra={"linhas": len(linhas)})
    return len(linhas)


def load_dim_pagamento_mart(engine: Engine, dim_pagamento_df: pd.DataFrame) -> int:
    """Persiste dim_pagamento (já agregada por pedido — ver dim_pagamento.py),
    preservando pagamento_sk já existentes (mesmo padrão das demais dims)."""
    if dim_pagamento_df.empty:
        logger.info("dim_pagamento_sem_registros_para_carregar")
        return 0

    colunas_a_persistir = [
        "order_id",
        "valor_total_pago",
        "forma_pagamento_principal",
        "qtd_parcelas",
        "qtd_metodos_pagamento",
    ]
    linhas = dim_pagamento_df[colunas_a_persistir].to_dict("records")

    stmt = pg_insert(dim_pagamento).values(linhas)
    colunas_atualizaveis = [c for c in colunas_a_persistir if c != "order_id"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["order_id"],
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info("dim_pagamento_carregada", extra={"linhas": len(linhas)})
    return len(linhas)


def _executar_select_como_dataframe(engine: Engine, stmt) -> pd.DataFrame:
    """Executa um SELECT do SQLAlchemy Core e retorna um DataFrame.

    Deliberadamente NÃO usa `pd.read_sql(stmt, conn)`: essa combinação quebra
    com "Query must be a string unless using sqlalchemy" na combinação
    pandas 3.0 + SQLAlchemy 1.4 (a versão que o Airflow 2.9 fixa como
    dependência) — bug real, encontrado rodando a DAG de verdade sob Airflow,
    não hipotético. Executar o SELECT diretamente via `conn.execute()` e
    montar o DataFrame manualmente é compatível com qualquer combinação de
    versões, porque não depende da detecção interna de tipo do pandas.
    """
    with engine.connect() as conn:
        resultado = conn.execute(stmt)
        return pd.DataFrame(resultado.fetchall(), columns=list(resultado.keys()))


def _ler_dim_customers_persistida(engine: Engine) -> pd.DataFrame:
    return _executar_select_como_dataframe(
        engine, select(dim_customers.c.customer_sk, dim_customers.c.customer_id)
    )


def _ler_dim_tempo_persistida(engine: Engine) -> pd.DataFrame:
    dim_tempo_persistida = _executar_select_como_dataframe(
        engine, select(dim_tempo.c.date_sk, dim_tempo.c.date)
    )
    # O driver do PostgreSQL retorna `date` como datetime.date puro; o merge
    # em build_fact_pedidos espera datetime64 (mesmo tipo usado no cálculo em
    # memória de build_dim_tempo) — sem essa normalização, o merge falha com
    # "You are trying to merge on datetime64[us] and object columns".
    dim_tempo_persistida["date"] = pd.to_datetime(dim_tempo_persistida["date"])
    return dim_tempo_persistida


def _ler_dim_products_persistida(engine: Engine) -> pd.DataFrame:
    return _executar_select_como_dataframe(
        engine, select(dim_products.c.product_sk, dim_products.c.product_id)
    )


def _ler_dim_sellers_persistida(engine: Engine) -> pd.DataFrame:
    return _executar_select_como_dataframe(
        engine, select(dim_sellers.c.seller_sk, dim_sellers.c.seller_id)
    )


def _ler_dim_pagamento_persistida(engine: Engine) -> pd.DataFrame:
    return _executar_select_como_dataframe(
        engine, select(dim_pagamento.c.pagamento_sk, dim_pagamento.c.order_id)
    )


def load_fact_pedidos_mart(
    engine: Engine,
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    reviews_por_pedido_df: pd.DataFrame,
    batch_date: date,
) -> int:
    """Constrói e persiste fact_pedidos, resolvendo as sk contra o banco.

    Pré-requisito: `load_dim_customers_mart`, `load_dim_tempo_mart`,
    `load_dim_products_mart`, `load_dim_sellers_mart` e
    `load_dim_pagamento_mart` já devem ter sido chamados para os
    clientes/datas/produtos/vendedores/pedidos presentes nos DataFrames de
    entrada — do contrário, os itens correspondentes são descartados (mesmo
    comportamento de `build_fact_pedidos` para chaves não resolvidas).

    `reviews_por_pedido_df` já deve estar deduplicado por pedido (ver
    `src/loading/dim_pagamento.resolve_review_score_por_pedido`).
    """
    dim_customers_persistida = _ler_dim_customers_persistida(engine)
    dim_tempo_persistida = _ler_dim_tempo_persistida(engine)
    dim_products_persistida = _ler_dim_products_persistida(engine)
    dim_sellers_persistida = _ler_dim_sellers_persistida(engine)
    dim_pagamento_persistida = _ler_dim_pagamento_persistida(engine)

    fato = build_fact_pedidos(
        orders_df,
        order_items_df,
        dim_customers_persistida,
        dim_tempo_persistida,
        dim_products_persistida,
        dim_sellers_persistida,
        dim_pagamento_persistida,
        reviews_por_pedido_df,
    )

    if fato.empty:
        logger.info("fact_pedidos_sem_registros_para_carregar")
        return 0

    fato = fato.assign(batch_date=batch_date)
    linhas = fato.to_dict("records")

    stmt = pg_insert(fact_pedidos).values(linhas)
    colunas_atualizaveis = [
        c for c in fato.columns if c not in ("order_id", "order_item_id")
    ]
    stmt = stmt.on_conflict_do_update(
        index_elements=["order_id", "order_item_id"],
        set_={coluna: stmt.excluded[coluna] for coluna in colunas_atualizaveis},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    logger.info(
        "fact_pedidos_carregado",
        extra={"linhas": len(linhas), "batch_date": str(batch_date)},
    )
    return len(linhas)
