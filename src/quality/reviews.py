"""Regras de qualidade de dados (RF03 da spec) para a entidade `order_reviews`.

Diferente das demais entidades, aqui NÃO rejeitamos `order_id` duplicado — o
dataset real legitimamente tem pedidos com mais de um review (ver
docs/ai/coding-rules.md e a nota em `src/models/schemas.ReviewRecord`). A
deduplicação por pedido acontece na camada de loading (`dim_pagamento`/fato),
não aqui: nesta camada validamos a linha em si, não a unicidade por pedido.
`review_id` duplicado, esse sim, é rejeitado — review_id é chave primária.
"""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import ReviewRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_REVIEW_ID = "review_id duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"


def validate_reviews_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[ReviewRecord], pd.DataFrame]:
    """Separa um DataFrame de reviews em registros válidos e rejeitados."""
    duplicados = find_duplicate_keys(dataframe, ["review_id"])

    registros_validos: list[ReviewRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)

        if (dados_linha["review_id"],) in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_REVIEW_ID}
            )
            continue

        try:
            review = ReviewRecord(**dados_linha)
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

        registros_validos.append(review)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "order_reviews",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
