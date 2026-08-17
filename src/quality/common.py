"""Helpers compartilhados por src/quality/{orders,customers,order_items}.py.

Extraído após o bug de pd.NA não reconhecido pelo pydantic encontrado na
implementação de `orders` — ver CHANGELOG e testing-rules.md sobre testes de
regressão.
"""

from __future__ import annotations

import pandas as pd


def normalize_row(row: pd.Series) -> dict:
    """Converte uma linha de DataFrame em dict, trocando pd.NA/NaN por None.

    Necessário porque o pydantic não reconhece o sentinel de nulo do pandas
    como ausência de valor — sem isso, campos opcionais vazios são rejeitados
    incorretamente como erro de tipo.
    """
    return {
        chave: (None if pd.isna(valor) else valor)
        for chave, valor in row.to_dict().items()
    }


def find_duplicate_keys(dataframe: pd.DataFrame, key_columns: list[str]) -> set[tuple]:
    """Retorna o conjunto de valores de chave (tupla) que aparecem mais de uma vez.

    `key_columns` pode ser uma chave simples (`["order_id"]`) ou composta
    (`["order_id", "order_item_id"]`).
    """
    contagem = dataframe.groupby(key_columns).size()
    duplicadas = contagem[contagem > 1]
    if len(key_columns) == 1:
        return {(valor,) for valor in duplicadas.index}
    return set(duplicadas.index)
