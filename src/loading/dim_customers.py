"""Construção de dim_customers, enriquecida com geolocalização (RF06 da spec).

Responsabilidade: transformação pura (DataFrame -> DataFrame), sem I/O. A
persistência em staging/mart é responsabilidade de `src/loading/load_staging.py`
e `src/loading/load_mart.py`.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.loading.geolocation import enrich_with_geolocation

logger = logging.getLogger(__name__)


def build_dim_customers(
    customers_df: pd.DataFrame, geolocation_df: pd.DataFrame
) -> pd.DataFrame:
    """Constrói dim_customers a partir de customers + geolocation.

    Entrada: DataFrames já validados (registros de CustomerRecord convertidos
    de volta a DataFrame, e o geolocation bruto). Saída: DataFrame com uma
    linha por `customer_id`, incluindo lat/lng médios e cidade/estado do CEP
    (podendo divergir levemente de `customer_city`/`customer_state`, que vêm
    diretamente do cadastro do cliente — ambos são mantidos para auditoria).

    A `customer_sk` calculada aqui é sequencial EM MEMÓRIA e só é estável
    dentro desta chamada — não deve ser persistida diretamente no banco. A sk
    de verdade, estável entre execuções, é gerada por IDENTITY em
    `mart.dim_customers` (ver `src/loading/load_mart.py`).
    """
    dim_customers = enrich_with_geolocation(
        customers_df, geolocation_df, zip_column="customer_zip_code_prefix"
    )

    sem_geo = dim_customers["geolocation_lat"].isna().sum()
    if sem_geo:
        logger.warning(
            "clientes_sem_geolocalizacao",
            extra={"quantidade": int(sem_geo), "total": len(dim_customers)},
        )

    dim_customers.insert(0, "customer_sk", range(1, len(dim_customers) + 1))

    logger.info("dim_customers_construida", extra={"linhas": len(dim_customers)})
    return dim_customers
