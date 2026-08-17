"""Regras de qualidade de dados (RF03 da spec) para a entidade `sellers`."""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import SellerRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_SELLER_ID = "seller_id duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"


def validate_sellers_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[SellerRecord], pd.DataFrame]:
    """Separa um DataFrame de vendedores em registros válidos e rejeitados."""
    duplicados = find_duplicate_keys(dataframe, ["seller_id"])

    registros_validos: list[SellerRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)

        if (dados_linha["seller_id"],) in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_SELLER_ID}
            )
            continue

        try:
            vendedor = SellerRecord(**dados_linha)
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

        registros_validos.append(vendedor)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "sellers",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
