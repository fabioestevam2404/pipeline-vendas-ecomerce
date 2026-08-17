"""Regras de qualidade de dados (RF03 da spec) para a entidade `orders`.

Diferente da validação de schema, aqui o erro é por LINHA, não por arquivo:
uma linha inválida é roteada para quarentena com o motivo registrado (RF04),
e as demais linhas do arquivo seguem o fluxo normal — nunca interrompemos o
processamento do arquivo inteiro por causa de uma linha ruim.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import OrderRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_ORDER_ID = "order_id duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"
REASON_FUTURE_PURCHASE_DATE = "order_purchase_timestamp no futuro"
REASON_DELIVERY_BEFORE_PURCHASE = (
    "order_estimated_delivery_date anterior a order_purchase_timestamp"
)


def _validar_regras_de_negocio(pedido: OrderRecord) -> str | None:
    """Aplica regras de qualidade que vão além da validação de tipo do pydantic.

    Retorna o motivo da rejeição, ou None se o registro passar em todas as regras.
    """
    agora = datetime.now(timezone.utc)
    data_compra = pedido.order_purchase_timestamp
    if data_compra.tzinfo is None:
        data_compra = data_compra.replace(tzinfo=timezone.utc)
    if data_compra > agora:
        return REASON_FUTURE_PURCHASE_DATE

    data_estimada = pedido.order_estimated_delivery_date
    if data_estimada.tzinfo is None:
        data_estimada = data_estimada.replace(tzinfo=timezone.utc)
    if data_estimada < data_compra:
        return REASON_DELIVERY_BEFORE_PURCHASE

    return None


def validate_orders_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[OrderRecord], pd.DataFrame]:
    """Separa um DataFrame de pedidos em registros válidos e rejeitados.

    Retorna (registros_validos, dataframe_rejeitados) onde o segundo tem todas
    as colunas originais mais uma coluna `motivo_rejeicao`.
    """
    duplicados = find_duplicate_keys(dataframe, ["order_id"])

    registros_validos: list[OrderRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        # pd.NA/NaN não são reconhecidos pelo pydantic como None; normalizamos
        # explicitamente para que campos opcionais vazios (ex.: data de entrega
        # ainda não ocorrida) sejam tratados como ausentes, não como erro de tipo.
        dados_linha = normalize_row(linha)

        if (dados_linha["order_id"],) in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_ORDER_ID}
            )
            continue

        try:
            pedido = OrderRecord(**dados_linha)
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

        motivo = _validar_regras_de_negocio(pedido)
        if motivo is not None:
            linhas_rejeitadas.append({**dados_linha, "motivo_rejeicao": motivo})
            continue

        registros_validos.append(pedido)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
