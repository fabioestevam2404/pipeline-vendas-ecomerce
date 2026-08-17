"""DAG diária do pipeline de vendas — orquestra o batch simulado (ADR-002).

Para cada execução (`ds`), processa os arquivos de `landing/<entidade>/<ds>.csv`
das entidades transacionais (orders, customers, order_items, order_payments,
order_reviews), populando staging e o data mart (dim_customers, dim_tempo,
dim_pagamento, fact_pedidos).

Pré-requisitos:
1. `python -m scripts.simulate_daily_batches` já ter sido rodado, populando a
   landing zone com os arquivos particionados por dia.
2. `pipeline_vendas_seed_reference_dag` já ter rodado ao menos uma vez, para
   que `dim_products`/`dim_sellers` existam (o fato depende dessas sk).

NOTA DE TRANSPARÊNCIA: mesma observação da DAG de seed — escrita seguindo a
TaskFlow API do Airflow 2.x, mas não executada/importada de fato neste
ambiente de desenvolvimento. Validar com `airflow dags list-import-errors`
no ambiente real (`docker-compose.yml`).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException

from src.config import load_settings
from src.db import get_engine
from src.ingestion.file_reader import read_csv_file
from src.ingestion.schema_validator import validate_schema
from src.loading.dim_customers import build_dim_customers
from src.loading.dim_pagamento import (
    build_dim_pagamento,
    resolve_review_score_por_pedido,
)
from src.loading.dim_tempo import build_dim_tempo
from src.loading.load_mart import (
    create_mart_schema,
    load_dim_customers_mart,
    load_dim_pagamento_mart,
    load_dim_tempo_mart,
    load_fact_pedidos_mart,
)
from src.loading.load_staging import (
    create_staging_schema,
    load_customers_staging,
    load_order_items_staging,
    load_orders_staging,
    load_payments_staging,
    load_reviews_staging,
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
from src.quality.quarantine import write_rejected
from src.quality.reviews import validate_reviews_dataframe

logger = logging.getLogger(__name__)


def _arquivo_do_dia(entidade: str, ds: str):
    settings = load_settings()
    caminho = settings.landing_zone_dir / entidade / f"{ds}.csv"
    if not caminho.exists():
        # Dia sem arquivo (ex.: nenhum pedido nessa data simulada) não é erro
        # — apenas não há o que processar. Ver docs/specs, "Disponibilidade
        # e recuperação": falha parcial não deve derrubar o pipeline.
        raise AirflowSkipException(f"Nenhum arquivo para '{entidade}' em {ds}")
    return caminho, settings


@dag(
    dag_id="pipeline_vendas_daily_dag",
    description="Pipeline diário: ingestão -> qualidade -> staging -> mart",
    schedule="@daily",
    start_date=datetime(2017, 1, 1),  # noqa: DTZ001 (convencao Airflow: naive = UTC)
    catchup=True,
    tags=["pipeline-vendas", "diario"],
)
def pipeline_vendas_daily_dag() -> None:
    @task
    def ensure_schemas() -> None:
        settings = load_settings()
        engine = get_engine(settings)
        create_staging_schema(engine)
        create_mart_schema(engine)
        create_reporting_views(engine)

    @task
    def process_orders(ds: str) -> int:
        caminho, settings = _arquivo_do_dia("orders", ds)
        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        dataframe = read_csv_file(caminho)
        validate_schema(dataframe, ORDERS_EXPECTED_COLUMNS)
        validos, rejeitados = validate_orders_dataframe(dataframe)
        write_rejected(rejeitados, settings.quarantine_dir, "orders", batch_date)

        load_orders_staging(engine, validos, batch_date)

        dim_tempo_df = build_dim_tempo(pd.DataFrame([o.model_dump() for o in validos]))
        load_dim_tempo_mart(engine, dim_tempo_df)

        return len(validos)

    @task
    def process_customers(ds: str) -> int:
        caminho, settings = _arquivo_do_dia("customers", ds)
        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        dataframe = read_csv_file(caminho)
        validate_schema(dataframe, CUSTOMERS_EXPECTED_COLUMNS)
        validos, rejeitados = validate_customers_dataframe(dataframe)
        write_rejected(rejeitados, settings.quarantine_dir, "customers", batch_date)

        load_customers_staging(engine, validos, batch_date)

        geolocation_df = read_csv_file(
            settings.landing_zone_dir / "reference" / "geolocation.csv"
        )
        dim_customers_df = build_dim_customers(
            pd.DataFrame([c.model_dump() for c in validos]), geolocation_df
        )
        load_dim_customers_mart(engine, dim_customers_df)

        return len(validos)

    @task
    def process_order_items(ds: str) -> int:
        caminho, settings = _arquivo_do_dia("order_items", ds)
        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        dataframe = read_csv_file(caminho)
        validate_schema(dataframe, ORDER_ITEMS_EXPECTED_COLUMNS)
        validos, rejeitados = validate_order_items_dataframe(dataframe)
        write_rejected(rejeitados, settings.quarantine_dir, "order_items", batch_date)

        load_order_items_staging(engine, validos, batch_date)
        return len(validos)

    @task
    def process_payments(ds: str) -> int:
        caminho, settings = _arquivo_do_dia("order_payments", ds)
        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        dataframe = read_csv_file(caminho)
        validate_schema(dataframe, ORDER_PAYMENTS_EXPECTED_COLUMNS)
        validos, rejeitados = validate_payments_dataframe(dataframe)
        write_rejected(
            rejeitados, settings.quarantine_dir, "order_payments", batch_date
        )

        load_payments_staging(engine, validos, batch_date)

        dim_pagamento_df = build_dim_pagamento(
            pd.DataFrame([p.model_dump() for p in validos])
        )
        load_dim_pagamento_mart(engine, dim_pagamento_df)

        return len(validos)

    @task
    def process_reviews(ds: str) -> int:
        try:
            caminho, settings = _arquivo_do_dia("order_reviews", ds)
        except AirflowSkipException:
            # Nem todo dia tem review (cliente pode avaliar dias depois da
            # compra) — diferente das demais entidades, isso não interrompe
            # o restante do DAG, só o passo de review em si.
            return 0

        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        dataframe = read_csv_file(caminho)
        validate_schema(dataframe, ORDER_REVIEWS_EXPECTED_COLUMNS)
        validos, rejeitados = validate_reviews_dataframe(dataframe)
        write_rejected(rejeitados, settings.quarantine_dir, "order_reviews", batch_date)

        load_reviews_staging(engine, validos, batch_date)
        return len(validos)

    @task
    def build_fact(
        qtd_orders: int,
        qtd_customers: int,
        qtd_items: int,
        qtd_payments: int,
        qtd_reviews: int,
        ds: str,
    ) -> int:
        """Constrói fact_pedidos do dia. Depende de TODAS as tasks acima via
        os parâmetros — garante que staging/mart de cada entidade já rodou.
        `ds` é injetado automaticamente pelo Airflow (contexto de execução),
        não deve ser passado explicitamente na chamada da task."""
        del qtd_orders, qtd_customers, qtd_payments, qtd_reviews  # apenas força a ordem
        if qtd_items == 0:
            raise AirflowSkipException(f"Nenhum item de pedido em {ds}, nada a fazer")

        caminho_orders, settings = _arquivo_do_dia("orders", ds)
        caminho_items, _ = _arquivo_do_dia("order_items", ds)
        engine = get_engine(settings)
        batch_date = datetime.strptime(ds, "%Y-%m-%d").date()  # noqa: DTZ007

        orders_df = read_csv_file(caminho_orders)
        order_items_df = read_csv_file(caminho_items)

        caminho_reviews = settings.landing_zone_dir / "order_reviews" / f"{ds}.csv"
        if caminho_reviews.exists():
            reviews_df = read_csv_file(caminho_reviews)
            reviews_por_pedido = resolve_review_score_por_pedido(reviews_df)
        else:
            reviews_por_pedido = pd.DataFrame(columns=["order_id", "review_score"])

        return load_fact_pedidos_mart(
            engine, orders_df, order_items_df, reviews_por_pedido, batch_date
        )

    schemas_prontos = ensure_schemas()
    qtd_orders = process_orders()
    qtd_customers = process_customers()
    qtd_items = process_order_items()
    qtd_payments = process_payments()
    qtd_reviews = process_reviews()

    schemas_prontos >> [qtd_orders, qtd_customers, qtd_items, qtd_payments, qtd_reviews]
    build_fact(
        qtd_orders=qtd_orders,
        qtd_customers=qtd_customers,
        qtd_items=qtd_items,
        qtd_payments=qtd_payments,
        qtd_reviews=qtd_reviews,
    )


pipeline_vendas_daily_dag()
