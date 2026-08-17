"""Construção de dim_sellers, enriquecida com geolocalização (RF06 da spec).

Espelha `dim_customers.py` (mesmo padrão de enriquecimento via CEP), usando o
helper compartilhado `src/loading/geolocation.py`.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.loading.geolocation import enrich_with_geolocation

logger = logging.getLogger(__name__)


def build_dim_sellers(
    sellers_df: pd.DataFrame, geolocation_df: pd.DataFrame
) -> pd.DataFrame:
    """Constrói dim_sellers a partir de sellers + geolocation.

    A `seller_sk` calculada aqui é sequencial EM MEMÓRIA e só é estável dentro
    desta chamada — a sk de verdade, estável entre execuções, é gerada por
    IDENTITY em `mart.dim_sellers` (ver `src/loading/load_mart.py`), no mesmo
    padrão já usado para `dim_customers.customer_sk`.
    """
    dim_sellers = enrich_with_geolocation(
        sellers_df, geolocation_df, zip_column="seller_zip_code_prefix"
    )

    sem_geo = dim_sellers["geolocation_lat"].isna().sum()
    if sem_geo:
        logger.warning(
            "vendedores_sem_geolocalizacao",
            extra={"quantidade": int(sem_geo), "total": len(dim_sellers)},
        )

    dim_sellers.insert(0, "seller_sk", range(1, len(dim_sellers) + 1))

    logger.info("dim_sellers_construida", extra={"linhas": len(dim_sellers)})
    return dim_sellers
