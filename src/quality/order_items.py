"""Regras de qualidade de dados (RF03 da spec) para a entidade `order_items`.

Granularidade: uma linha por item de pedido. Chave composta
(order_id, order_item_id) — dois itens do mesmo pedido têm order_item_id
diferentes (1, 2, 3...).
"""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import ValidationError

from src.models.schemas import OrderItemRecord
from src.quality.common import find_duplicate_keys, normalize_row

logger = logging.getLogger(__name__)

REASON_DUPLICATE_ITEM_KEY = "(order_id, order_item_id) duplicado no arquivo"
REASON_SCHEMA_VALIDATION = "falha de validação de schema/tipo: {detalhe}"
REASON_ORPHAN_ORDER_ID = "order_id não existe em orders (chave órfã)"


def validate_order_items_dataframe(
    dataframe: pd.DataFrame,
    known_order_ids: set[str] | None = None,
) -> tuple[list[OrderItemRecord], pd.DataFrame]:
    """Separa um DataFrame de itens de pedido em registros válidos e rejeitados.

    `known_order_ids`: conjunto de order_id já validados na entidade `orders`
    (ver spec, "Casos de erro e borda": chaves estrangeiras órfãs). Se
    informado, itens referenciando um order_id inexistente são rejeitados.
    Se None, essa checagem é pulada (útil para testar `order_items` de forma
    isolada, sem depender de `orders` já carregado).
    """
    duplicados = find_duplicate_keys(dataframe, ["order_id", "order_item_id"])

    registros_validos: list[OrderItemRecord] = []
    linhas_rejeitadas: list[dict] = []

    for _, linha in dataframe.iterrows():
        dados_linha = normalize_row(linha)
        chave = (dados_linha.get("order_id"), dados_linha.get("order_item_id"))

        if chave in duplicados:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_DUPLICATE_ITEM_KEY}
            )
            continue

        try:
            item = OrderItemRecord(**dados_linha)
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

        if known_order_ids is not None and item.order_id not in known_order_ids:
            linhas_rejeitadas.append(
                {**dados_linha, "motivo_rejeicao": REASON_ORPHAN_ORDER_ID}
            )
            continue

        registros_validos.append(item)

    rejeitados_df = pd.DataFrame(linhas_rejeitadas)

    logger.info(
        "validacao_concluida",
        extra={
            "entidade": "order_items",
            "total_linhas": len(dataframe),
            "validas": len(registros_validos),
            "rejeitadas": len(rejeitados_df),
        },
    )

    return registros_validos, rejeitados_df
