"""Construção de dim_pagamento (RF06 da spec), agregada por PEDIDO.

Decisão de design deliberada: `order_payments` está no grão de
pedido+parcela/método (um pedido pode ter várias linhas), enquanto
`fact_pedidos` está no grão de item de pedido. Se juntássemos `order_payments`
bruto diretamente no fato (grão de item), um pedido com 2 itens e pago em 2
parcelas viraria 4 linhas no fato — inflando artificialmente métricas de
receita (fan-out clássico em modelagem dimensional).

Por isso, `dim_pagamento` agrega os pagamentos POR PEDIDO antes de virar uma
dimensão: 1 linha por `order_id`, com valor total pago, forma de pagamento
predominante (a de maior valor) e o maior número de parcelas usado. Isso dá
um `pagamento_sk` que pode ser juntado ao fato pelo `order_id` sem multiplicar
linhas — o mesmo padrão problema/solução vale para `order_reviews`, tratado
separadamente em `resolve_review_score_por_pedido` (mesmo módulo).
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_dim_pagamento(payments_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega `order_payments` por `order_id`, uma linha por pedido.

    Colunas de saída: `order_id`, `valor_total_pago` (soma de payment_value),
    `forma_pagamento_principal` (payment_type da linha de maior valor),
    `qtd_parcelas` (maior payment_installments entre as linhas do pedido),
    `qtd_metodos_pagamento` (quantidade de linhas de pagamento do pedido —
    >1 indica pagamento dividido em mais de um método/parcela registrada).

    A `pagamento_sk` calculada aqui é sequencial EM MEMÓRIA e só é estável
    dentro desta chamada — a sk de verdade, estável entre execuções, é gerada
    por IDENTITY em `mart.dim_pagamento` (mesmo padrão das demais dimensões).
    """
    if payments_df.empty:
        return pd.DataFrame(
            columns=[
                "pagamento_sk",
                "order_id",
                "valor_total_pago",
                "forma_pagamento_principal",
                "qtd_parcelas",
                "qtd_metodos_pagamento",
            ]
        )

    valor_total = payments_df.groupby("order_id")["payment_value"].sum()
    qtd_parcelas = payments_df.groupby("order_id")["payment_installments"].max()
    qtd_metodos = payments_df.groupby("order_id").size()

    # Forma de pagamento principal = payment_type da linha de maior valor
    # dentro do pedido (critério simples e defensável para "método dominante").
    indice_maior_valor = payments_df.groupby("order_id")["payment_value"].idxmax()
    forma_principal = payments_df.loc[indice_maior_valor].set_index("order_id")[
        "payment_type"
    ]

    dim_pagamento = pd.DataFrame(
        {
            "order_id": valor_total.index,
            "valor_total_pago": valor_total.values,
            "forma_pagamento_principal": forma_principal.reindex(
                valor_total.index
            ).values,
            "qtd_parcelas": qtd_parcelas.reindex(valor_total.index).values,
            "qtd_metodos_pagamento": qtd_metodos.reindex(valor_total.index).values,
        }
    )

    pedidos_com_metodo_dividido = (dim_pagamento["qtd_metodos_pagamento"] > 1).sum()
    if pedidos_com_metodo_dividido:
        logger.info(
            "pedidos_com_pagamento_dividido",
            extra={"quantidade": int(pedidos_com_metodo_dividido)},
        )

    dim_pagamento.insert(0, "pagamento_sk", range(1, len(dim_pagamento) + 1))

    logger.info("dim_pagamento_construida", extra={"linhas": len(dim_pagamento)})
    return dim_pagamento


def resolve_review_score_por_pedido(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Deduplica `order_reviews` para 1 linha por `order_id` (evita fan-out).

    Critério de desempate: mantém o review com `review_creation_date` mais
    recente por pedido. Pedidos com mais de um review geram um log — é um
    caso real do dataset, não hipotético (ver docstring do módulo).
    """
    if reviews_df.empty:
        return pd.DataFrame(columns=["order_id", "review_score"])

    contagem_por_pedido = reviews_df.groupby("order_id").size()
    pedidos_com_multiplos_reviews = (contagem_por_pedido > 1).sum()
    if pedidos_com_multiplos_reviews:
        logger.info(
            "pedidos_com_multiplos_reviews",
            extra={"quantidade": int(pedidos_com_multiplos_reviews)},
        )

    reviews_ordenados = reviews_df.sort_values("review_creation_date")
    review_mais_recente_por_pedido = reviews_ordenados.drop_duplicates(
        subset="order_id", keep="last"
    )

    return review_mais_recente_por_pedido[["order_id", "review_score"]]
