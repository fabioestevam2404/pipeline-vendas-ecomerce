"""Executa o pipeline completo para um dia simulado, sem depender do Airflow.

Este é o script que faltava para o runbook de validação Docker funcionar de
verdade: `docker compose exec app python src/loading/load_mart.py` não fazia
nada, porque `load_mart.py` é um módulo de biblioteca (só funções), não um
entrypoint. Este script chama as mesmas funções que as DAGs em `dags/`
chamam, na mesma ordem, mas de forma síncrona e sem precisar do Airflow de
pé — útil para validação rápida via Docker ou execução manual local.

Uso:
    python -m scripts.run_pipeline --seed-reference
    python -m scripts.run_pipeline --date 2017-05-10
    python -m scripts.run_pipeline --seed-reference --date 2017-05-10

Pré-requisito: `python -m scripts.simulate_daily_batches` já ter populado
`data/landing/` (ver README.md).
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime

import pandas as pd

from src.config import Settings, load_settings
from src.db import get_engine
from src.ingestion.file_reader import read_csv_file
from src.ingestion.schema_validator import validate_schema
from src.loading.dim_customers import build_dim_customers
from src.loading.dim_pagamento import (
    build_dim_pagamento,
    resolve_review_score_por_pedido,
)
from src.loading.dim_products import build_dim_products
from src.loading.dim_sellers import build_dim_sellers
from src.loading.dim_tempo import build_dim_tempo
from src.loading.load_mart import (
    create_mart_schema,
    load_dim_customers_mart,
    load_dim_pagamento_mart,
    load_dim_products_mart,
    load_dim_sellers_mart,
    load_dim_tempo_mart,
    load_fact_pedidos_mart,
)
from src.loading.load_staging import (
    create_staging_schema,
    load_customers_staging,
    load_order_items_staging,
    load_orders_staging,
    load_payments_staging,
    load_products_staging,
    load_reviews_staging,
    load_sellers_staging,
)
from src.loading.reporting_views import create_reporting_views
from src.models.schemas import (
    CUSTOMERS_EXPECTED_COLUMNS,
    ORDER_ITEMS_EXPECTED_COLUMNS,
    ORDER_PAYMENTS_EXPECTED_COLUMNS,
    ORDER_REVIEWS_EXPECTED_COLUMNS,
    ORDERS_EXPECTED_COLUMNS,
)
from src.quality.customers import validate_customers_dataframe
from src.quality.order_items import validate_order_items_dataframe
from src.quality.orders import validate_orders_dataframe
from src.quality.payments import validate_payments_dataframe
from src.quality.products import validate_products_dataframe
from src.quality.quarantine import write_rejected
from src.quality.reviews import validate_reviews_dataframe
from src.quality.sellers import validate_sellers_dataframe

logger = logging.getLogger(__name__)


def seed_reference_data(settings: Settings) -> None:
    """Carrega products + sellers (entidades de referência, não particionadas).

    Espelha `dags/seed_reference_data_dag.py` — mesma lógica, execução síncrona.
    """
    engine = get_engine(settings)

    products_df = read_csv_file(
        settings.landing_zone_dir / "reference" / "products.csv"
    )
    translation_df = read_csv_file(
        settings.landing_zone_dir / "reference" / "category_translation.csv"
    )
    validos_produtos, rejeitados_produtos = validate_products_dataframe(products_df)
    if not rejeitados_produtos.empty:
        logger.warning(
            "produtos_rejeitados", extra={"quantidade": len(rejeitados_produtos)}
        )
    batch_date = datetime.now().date()  # noqa: DTZ005 (apenas data, sem uso de hora)
    load_products_staging(engine, validos_produtos, batch_date)
    dim_products_df = build_dim_products(
        pd.DataFrame([p.model_dump() for p in validos_produtos]), translation_df
    )
    qtd_products = load_dim_products_mart(engine, dim_products_df)
    logger.info("seed_products_concluido", extra={"linhas": qtd_products})

    sellers_df = read_csv_file(settings.landing_zone_dir / "reference" / "sellers.csv")
    geolocation_df = read_csv_file(
        settings.landing_zone_dir / "reference" / "geolocation.csv"
    )
    validos_sellers, rejeitados_sellers = validate_sellers_dataframe(sellers_df)
    if not rejeitados_sellers.empty:
        logger.warning(
            "vendedores_rejeitados", extra={"quantidade": len(rejeitados_sellers)}
        )
    load_sellers_staging(engine, validos_sellers, batch_date)
    dim_sellers_df = build_dim_sellers(
        pd.DataFrame([s.model_dump() for s in validos_sellers]), geolocation_df
    )
    qtd_sellers = load_dim_sellers_mart(engine, dim_sellers_df)
    logger.info("seed_sellers_concluido", extra={"linhas": qtd_sellers})


def _processar_entidade_generica(
    settings: Settings,
    engine,
    entidade: str,
    colunas_esperadas: list[str],
    validar_fn,
    carregar_staging_fn,
    target_date: date,
) -> int:
    """Ingestão + validação de schema + qualidade + carga em staging para
    uma entidade transacional simples (sem etapa de mart própria)."""
    caminho = settings.landing_zone_dir / entidade / f"{target_date.isoformat()}.csv"
    if not caminho.exists():
        logger.info("arquivo_ausente_para_o_dia", extra={"entidade": entidade})
        return 0

    dataframe = read_csv_file(caminho)
    validate_schema(dataframe, colunas_esperadas)
    validos, rejeitados = validar_fn(dataframe)
    write_rejected(rejeitados, settings.quarantine_dir, entidade, target_date)
    return carregar_staging_fn(engine, validos, target_date)


def process_day(settings: Settings, target_date: date) -> None:
    """Roda o pipeline completo (staging + mart) para um dia simulado.

    Espelha `dags/pipeline_vendas_daily_dag.py` — mesma lógica, execução
    síncrona, sem precisar do Airflow. Requer que `seed_reference_data` já
    tenha sido rodado ao menos uma vez (senão `produto_sk`/`vendedor_sk` não
    resolvem e o fato fica vazio — comportamento intencional, não um bug).
    """
    engine = get_engine(settings)

    qtd_orders = _processar_entidade_generica(
        settings,
        engine,
        "orders",
        ORDERS_EXPECTED_COLUMNS,
        validate_orders_dataframe,
        load_orders_staging,
        target_date,
    )
    qtd_customers = _processar_entidade_generica(
        settings,
        engine,
        "customers",
        CUSTOMERS_EXPECTED_COLUMNS,
        validate_customers_dataframe,
        load_customers_staging,
        target_date,
    )
    qtd_items = _processar_entidade_generica(
        settings,
        engine,
        "order_items",
        ORDER_ITEMS_EXPECTED_COLUMNS,
        validate_order_items_dataframe,
        load_order_items_staging,
        target_date,
    )
    qtd_payments = _processar_entidade_generica(
        settings,
        engine,
        "order_payments",
        ORDER_PAYMENTS_EXPECTED_COLUMNS,
        validate_payments_dataframe,
        load_payments_staging,
        target_date,
    )
    qtd_reviews = _processar_entidade_generica(
        settings,
        engine,
        "order_reviews",
        ORDER_REVIEWS_EXPECTED_COLUMNS,
        validate_reviews_dataframe,
        load_reviews_staging,
        target_date,
    )

    logger.info(
        "staging_do_dia_concluido",
        extra={
            "data": target_date.isoformat(),
            "orders": qtd_orders,
            "customers": qtd_customers,
            "order_items": qtd_items,
            "order_payments": qtd_payments,
            "order_reviews": qtd_reviews,
        },
    )

    if qtd_orders == 0 or qtd_items == 0:
        logger.info("nada_a_fazer_no_mart", extra={"data": target_date.isoformat()})
        return

    caminho_orders = (
        settings.landing_zone_dir / "orders" / f"{target_date.isoformat()}.csv"
    )
    caminho_items = (
        settings.landing_zone_dir / "order_items" / f"{target_date.isoformat()}.csv"
    )
    orders_df = read_csv_file(caminho_orders)
    order_items_df = read_csv_file(caminho_items)

    geolocation_df = read_csv_file(
        settings.landing_zone_dir / "reference" / "geolocation.csv"
    )
    customers_validos, _ = validate_customers_dataframe(
        read_csv_file(
            settings.landing_zone_dir / "customers" / f"{target_date.isoformat()}.csv"
        )
    )
    dim_customers_df = build_dim_customers(
        pd.DataFrame([c.model_dump() for c in customers_validos]), geolocation_df
    )
    load_dim_customers_mart(engine, dim_customers_df)

    load_dim_tempo_mart(engine, build_dim_tempo(orders_df))

    caminho_payments = (
        settings.landing_zone_dir / "order_payments" / f"{target_date.isoformat()}.csv"
    )
    if caminho_payments.exists():
        payments_validos, _ = validate_payments_dataframe(
            read_csv_file(caminho_payments)
        )
        load_dim_pagamento_mart(
            engine,
            build_dim_pagamento(
                pd.DataFrame([p.model_dump() for p in payments_validos])
            ),
        )

    caminho_reviews = (
        settings.landing_zone_dir / "order_reviews" / f"{target_date.isoformat()}.csv"
    )
    if caminho_reviews.exists():
        reviews_por_pedido = resolve_review_score_por_pedido(
            read_csv_file(caminho_reviews)
        )
    else:
        reviews_por_pedido = pd.DataFrame(columns=["order_id", "review_score"])

    linhas_fato = load_fact_pedidos_mart(
        engine, orders_df, order_items_df, reviews_por_pedido, target_date
    )
    logger.info(
        "fact_pedidos_do_dia_concluido",
        extra={"data": target_date.isoformat(), "linhas": linhas_fato},
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-reference",
        action="store_true",
        help="Carrega products/sellers antes de processar o dia (necessário na primeira execução).",
    )
    parser.add_argument("--date", type=str, default=None, help="AAAA-MM-DD")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    settings = load_settings()

    engine = get_engine(settings)
    create_staging_schema(engine)
    create_mart_schema(engine)
    create_reporting_views(engine)

    if args.seed_reference:
        seed_reference_data(settings)

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()  # noqa: DTZ007
        process_day(settings, target_date)
    elif not args.seed_reference:
        parser_msg = "Nada a fazer: informe --date, --seed-reference, ou ambos."
        raise SystemExit(parser_msg)


if __name__ == "__main__":
    main()
