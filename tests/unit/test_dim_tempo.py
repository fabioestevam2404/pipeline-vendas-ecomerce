from __future__ import annotations

import pandas as pd

from src.loading.dim_tempo import build_dim_tempo


def _orders() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"order_id": "ord-1", "order_purchase_timestamp": "2017-05-10 10:00:00"},
            {"order_id": "ord-2", "order_purchase_timestamp": "2017-05-10 15:30:00"},
            {"order_id": "ord-3", "order_purchase_timestamp": "2017-05-13 09:00:00"},
        ]
    )


def test_dim_tempo_tem_uma_linha_por_data_distinta() -> None:
    dim_tempo = build_dim_tempo(_orders())

    # 2017-05-10 aparece duas vezes em orders, mas deve virar 1 linha em dim_tempo.
    assert len(dim_tempo) == 2
    assert dim_tempo["date_sk"].is_unique


def test_date_sk_segue_formato_aaaammdd() -> None:
    dim_tempo = build_dim_tempo(_orders())

    linha = dim_tempo[dim_tempo["date_sk"] == 20170510]
    assert not linha.empty


def test_fim_de_semana_e_calculado_corretamente() -> None:
    dim_tempo = build_dim_tempo(_orders())

    # 2017-05-13 é um sábado.
    linha = dim_tempo[dim_tempo["date_sk"] == 20170513].iloc[0]
    assert linha["fim_de_semana"]
    assert linha["dia_da_semana"] == "sábado"

    # 2017-05-10 é uma quarta-feira.
    linha = dim_tempo[dim_tempo["date_sk"] == 20170510].iloc[0]
    assert not linha["fim_de_semana"]
