"""Construção de dim_tempo (RF06 da spec) a partir das datas de compra de `orders`.

Diferente de uma dim_tempo tradicional (calendário completo pré-gerado para um
range de anos), aqui geramos apenas as datas efetivamente presentes em
`order_purchase_timestamp` — suficiente para o propósito do projeto e mais
simples de manter sincronizada. Se o projeto evoluir para consultas que
precisem de datas sem pedido (ex.: "dias sem venda"), isso vira uma nova ADR.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Data em português, consistente com o restante da documentação do projeto.
_DIAS_DA_SEMANA_PT = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def build_dim_tempo(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Gera dim_tempo a partir das datas distintas em `order_purchase_timestamp`.

    Colunas: date_sk (int, formato AAAAMMDD — padrão de mercado para chave de
    data), date, ano, mes, trimestre, dia, dia_da_semana, fim_de_semana.
    """
    datas = pd.to_datetime(orders_df["order_purchase_timestamp"]).dt.normalize()
    datas_distintas = pd.Series(datas.unique()).sort_values().reset_index(drop=True)

    dim_tempo = pd.DataFrame({"date": datas_distintas})
    dim_tempo["date_sk"] = dim_tempo["date"].dt.strftime("%Y%m%d").astype(int)
    dim_tempo["ano"] = dim_tempo["date"].dt.year
    dim_tempo["mes"] = dim_tempo["date"].dt.month
    dim_tempo["trimestre"] = dim_tempo["date"].dt.quarter
    dim_tempo["dia"] = dim_tempo["date"].dt.day
    dim_tempo["dia_da_semana"] = dim_tempo["date"].dt.dayofweek.map(_DIAS_DA_SEMANA_PT)
    dim_tempo["fim_de_semana"] = dim_tempo["date"].dt.dayofweek.isin([5, 6])

    logger.info("dim_tempo_construida", extra={"linhas": len(dim_tempo)})
    return dim_tempo[
        [
            "date_sk",
            "date",
            "ano",
            "mes",
            "trimestre",
            "dia",
            "dia_da_semana",
            "fim_de_semana",
        ]
    ]
