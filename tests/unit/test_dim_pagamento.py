from __future__ import annotations

import pandas as pd

from src.loading.dim_pagamento import (
    build_dim_pagamento,
    resolve_review_score_por_pedido,
)


def test_dim_pagamento_agrega_por_pedido() -> None:
    payments_df = pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "payment_sequential": 1,
                "payment_type": "voucher",
                "payment_installments": 1,
                "payment_value": 20.0,
            },
            {
                "order_id": "ord-1",
                "payment_sequential": 2,
                "payment_type": "credit_card",
                "payment_installments": 3,
                "payment_value": 100.0,
            },
        ]
    )

    dim_pagamento = build_dim_pagamento(payments_df)

    assert len(dim_pagamento) == 1
    linha = dim_pagamento.iloc[0]
    assert linha["valor_total_pago"] == 120.0
    # forma_pagamento_principal = payment_type da linha de MAIOR valor.
    assert linha["forma_pagamento_principal"] == "credit_card"
    assert linha["qtd_metodos_pagamento"] == 2


def test_dim_pagamento_nao_causa_fanout_no_grao_de_pedido() -> None:
    payments_df = pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 2,
                "payment_value": 50.0,
            },
            {
                "order_id": "ord-1",
                "payment_sequential": 2,
                "payment_type": "voucher",
                "payment_installments": 1,
                "payment_value": 10.0,
            },
            {
                "order_id": "ord-2",
                "payment_sequential": 1,
                "payment_type": "boleto",
                "payment_installments": 1,
                "payment_value": 30.0,
            },
        ]
    )

    dim_pagamento = build_dim_pagamento(payments_df)

    # 3 linhas de pagamento -> 2 pedidos distintos, não 3.
    assert len(dim_pagamento) == 2
    assert dim_pagamento["order_id"].is_unique


def test_resolve_review_score_deduplica_por_pedido() -> None:
    reviews_df = pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "review_score": 2,
                "review_creation_date": "2017-05-10 10:00:00",
            },
            {
                # Segundo review do MESMO pedido, mais recente -> deve prevalecer.
                "order_id": "ord-1",
                "review_score": 5,
                "review_creation_date": "2017-05-15 10:00:00",
            },
            {
                "order_id": "ord-2",
                "review_score": 4,
                "review_creation_date": "2017-05-12 10:00:00",
            },
        ]
    )

    resultado = resolve_review_score_por_pedido(reviews_df)

    assert len(resultado) == 2
    assert resultado["order_id"].is_unique
    score_ord1 = resultado.loc[resultado["order_id"] == "ord-1", "review_score"].iloc[0]
    assert score_ord1 == 5
