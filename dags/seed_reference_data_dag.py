"""DAG de seed das entidades de referência: products, sellers, category_translation.

Executada manualmente (schedule=None), não diariamente — produto/vendedor não
"chegam" em uma data específica como um pedido; são catálogos que existem de
uma vez, atualizados por reprocessamento manual quando necessário. Rodar essa
DAG uma vez, antes da DAG diária (`pipeline_vendas_daily_dag`), que depende de
`dim_products`/`dim_sellers` já estarem populadas para resolver `produto_sk`/
`vendedor_sk` no fato.

Pré-requisito: `python -m scripts.simulate_daily_batches` já ter sido rodado
ao menos uma vez, populando `landing/reference/*.csv`.

NOTA DE TRANSPARÊNCIA: esta DAG foi escrita seguindo a TaskFlow API do
Airflow 2.x, mas não pôde ser executada/importada de fato neste ambiente de
desenvolvimento (rodar o Airflow completo — metastore, scheduler, webserver —
é peso desproporcional para o sandbox usado para construir o projeto). Validar
com `airflow dags list-import-errors` assim que o serviço do Airflow do
`docker-compose.yml` estiver de pé.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from airflow.decorators import dag, task

from src.config import load_settings
from src.db import get_engine
from src.ingestion.file_reader import read_csv_file
from src.loading.dim_products import build_dim_products
from src.loading.dim_sellers import build_dim_sellers
from src.loading.load_mart import (
    create_mart_schema,
    load_dim_products_mart,
    load_dim_sellers_mart,
)
from src.loading.load_staging import (
    create_staging_schema,
    load_products_staging,
    load_sellers_staging,
)
from src.loading.reporting_views import create_reporting_views
from src.quality.products import validate_products_dataframe
from src.quality.sellers import validate_sellers_dataframe

logger = logging.getLogger(__name__)


@dag(
    dag_id="pipeline_vendas_seed_reference_dag",
    description="Carrega products, sellers e category_translation (execução manual)",
    schedule=None,
    start_date=datetime(2017, 1, 1),  # noqa: DTZ001 (convencao Airflow: naive = UTC)
    catchup=False,
    tags=["pipeline-vendas", "seed", "referencia"],
)
def pipeline_vendas_seed_reference_dag() -> None:
    @task
    def ensure_schemas() -> None:
        settings = load_settings()
        engine = get_engine(settings)
        create_staging_schema(engine)
        create_mart_schema(engine)
        create_reporting_views(engine)

    @task
    def load_products() -> int:
        settings = load_settings()
        engine = get_engine(settings)

        products_df = read_csv_file(
            settings.landing_zone_dir / "reference" / "products.csv"
        )
        translation_df = read_csv_file(
            settings.landing_zone_dir / "reference" / "category_translation.csv"
        )

        validos, rejeitados = validate_products_dataframe(products_df)
        if not rejeitados.empty:
            logger.warning("produtos_rejeitados", extra={"quantidade": len(rejeitados)})

        _agora = datetime.now()  # noqa: DTZ005 (apenas data, sem uso de hora)
        batch_date = _agora.date()
        load_products_staging(engine, validos, batch_date)

        dim_products_df = build_dim_products(
            pd.DataFrame([p.model_dump() for p in validos]), translation_df
        )
        return load_dim_products_mart(engine, dim_products_df)

    @task
    def load_sellers() -> int:
        settings = load_settings()
        engine = get_engine(settings)

        sellers_df = read_csv_file(
            settings.landing_zone_dir / "reference" / "sellers.csv"
        )
        geolocation_df = read_csv_file(
            settings.landing_zone_dir / "reference" / "geolocation.csv"
        )

        validos, rejeitados = validate_sellers_dataframe(sellers_df)
        if not rejeitados.empty:
            logger.warning(
                "vendedores_rejeitados", extra={"quantidade": len(rejeitados)}
            )

        _agora = datetime.now()  # noqa: DTZ005 (apenas data, sem uso de hora)
        batch_date = _agora.date()
        load_sellers_staging(engine, validos, batch_date)

        dim_sellers_df = build_dim_sellers(
            pd.DataFrame([s.model_dump() for s in validos]), geolocation_df
        )
        return load_dim_sellers_mart(engine, dim_sellers_df)

    schemas_prontos = ensure_schemas()
    produtos_carregados = load_products()
    vendedores_carregados = load_sellers()
    schemas_prontos >> [produtos_carregados, vendedores_carregados]


pipeline_vendas_seed_reference_dag()
