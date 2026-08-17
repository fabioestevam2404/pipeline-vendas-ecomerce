"""Regras de qualidade de dados (RF03 da spec) para a entidade `order_payments`.

Granularidade: uma linha por parcela/método de pagamento de um pedido. Chave
composta (order_id, payment_sequential) — um pedido pago em 2 métodos tem 2
linhas com payment_sequential 1 e 2.
"""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import PaymentRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_PAYMENT_KEY = "(order_id, payment_sequential) duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"


def validate_payments_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[PaymentRecord], pd.DataFrame]:
    """Separa um DataFrame de pagamentos em registros válidos e rejeitados."""
    duplicados = find_duplicate_keys(dataframe, ["order_id", "payment_sequential"])

    registros_validos: list[PaymentRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)
        chave = (dados_linha.get("order_id"), dados_linha.get("payment_sequential"))

        if chave in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_PAYMENT_KEY}
            )
            continue

        try:
            pagamento = PaymentRecord(**dados_linha)
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

        registros_validos.append(pagamento)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "order_payments",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
