"""Regras de qualidade de dados (RF03 da spec) para a entidade `products`."""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import ProductRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_PRODUCT_ID = "product_id duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"


def validate_products_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[ProductRecord], pd.DataFrame]:
    """Separa um DataFrame de produtos em registros válidos e rejeitados.

    Produto sem `product_category_name` ou sem dimensões NÃO é rejeitado (é
    um nulo legítimo do dataset real). Produto com medida física negativa é.
    """
    duplicados = find_duplicate_keys(dataframe, ["product_id"])

    registros_validos: list[ProductRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)

        if (dados_linha["product_id"],) in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_PRODUCT_ID}
            )
            continue

        try:
            produto = ProductRecord(**dados_linha)
        except ValidationError as exc:
            linhas_rejeitadas.append(
                {
                    **dados_linha,
                    "motivo_rejeicao": REASON_SCHEMA_VALIDATION.format(
                        detalhe=exc.errors()[0]["msg"]
                    ),
                }
            )
            continue

        registros_validos.append(produto)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "products",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
