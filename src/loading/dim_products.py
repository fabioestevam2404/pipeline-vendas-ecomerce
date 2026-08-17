"""Construção de dim_products, com tradução de categoria PT->EN (RF06 da spec).

Produtos sem `product_category_name` (nulo legítimo no dataset real, ver
`src/models/schemas.ProductRecord`) ficam sem tradução — não são descartados.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_dim_products(
    products_df: pd.DataFrame, category_translation_df: pd.DataFrame
) -> pd.DataFrame:
    """Constrói dim_products a partir de products + product_category_name_translation.

    A `product_sk` calculada aqui é sequencial EM MEMÓRIA e só é estável
    dentro desta chamada — a sk de verdade, estável entre execuções, é gerada
    por IDENTITY em `mart.dim_products` (ver `src/loading/load_mart.py`).
    """
    dim_products = products_df.merge(
        category_translation_df,
        how="left",
        on="product_category_name",
    )

    sem_categoria = dim_products["product_category_name"].isna().sum()
    if sem_categoria:
        logger.info(
            "produtos_sem_categoria",
            extra={"quantidade": int(sem_categoria), "total": len(dim_products)},
        )

    sem_traducao = (
        dim_products["product_category_name"].notna()
        & dim_products["product_category_name_english"].isna()
    ).sum()
    if sem_traducao:
        logger.warning(
            "categorias_sem_traducao_em_ingles",
            extra={"quantidade": int(sem_traducao)},
        )

    dim_products.insert(0, "product_sk", range(1, len(dim_products) + 1))

    # 610 produtos reais do dataset Olist não têm essas 3 colunas preenchidas.
    # NaN num psycopg2 INSERT vira um cast implícito float8->integer no
    # Postgres, que levanta "integer out of range" (não "invalid syntax") —
    # normaliza para None explicitamente, com dtype=object (mesmo padrão de
    # `review_score` em fact_pedidos.py, ver comentário lá).
    for coluna in (
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
    ):
        dim_products[coluna] = pd.Series(
            [int(v) if pd.notna(v) else None for v in dim_products[coluna]],
            index=dim_products.index,
            dtype=object,
        )

    logger.info("dim_products_construida", extra={"linhas": len(dim_products)})
    return dim_products
