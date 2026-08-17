"""Regras de qualidade de dados (RF03 da spec) para a entidade `customers`."""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import CustomerRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_CUSTOMER_ID = "customer_id duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"


def validate_customers_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[CustomerRecord], pd.DataFrame]:
    """Separa um DataFrame de clientes em registros válidos e rejeitados.

    `customer_id` é único por linha no dataset Olist (um id novo por pedido);
    duplicidade aqui indica arquivo corrompido ou reprocessamento indevido.
    """
    duplicados = find_duplicate_keys(dataframe, ["customer_id"])

    registros_validos: list[CustomerRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)

        if (dados_linha["customer_id"],) in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_CUSTOMER_ID}
            )
            continue

        try:
            cliente = CustomerRecord(**dados_linha)
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

        registros_validos.append(cliente)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "customers",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
