from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.order_items import (
    REASON_DUPLICATE_ITEM_KEY,
    REASON_ORPHAN_ORDER_ID,
    validate_order_items_dataframe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "order_items_sample.csv", dtype=str, keep_default_na=True
    )


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_order_items_dataframe(dataframe)

    chaves_validas = {(item.order_id, item.order_item_id) for item in validos}
    assert ("ord-0001", 1) in chaves_validas
    assert ("ord-0001", 2) in chaves_validas
    assert ("ord-0002", 1) in chaves_validas


def test_preco_negativo_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_order_items_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0009"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_product_id_ausente_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_order_items_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0010"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_chave_composta_duplicada_e_rejeitada() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_order_items_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["order_id"] == "ord-0011"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_ITEM_KEY).all()


def test_order_id_orfao_e_rejeitado_quando_known_order_ids_informado() -> None:
    dataframe = _carregar_amostra()
    known_order_ids = {"ord-0001", "ord-0002"}

    validos, rejeitados = validate_order_items_dataframe(
        dataframe, known_order_ids=known_order_ids
    )

    linha = rejeitados[rejeitados["order_id"] == "ord-0099"].iloc[0]
    assert linha["motivo_rejeicao"] == REASON_ORPHAN_ORDER_ID
    assert all(item.order_id in known_order_ids for item in validos)


def test_sem_known_order_ids_nao_aplica_checagem_de_orfao() -> None:
    dataframe = _carregar_amostra()

    validos, rejeitados = validate_order_items_dataframe(
        dataframe, known_order_ids=None
    )

    assert "ord-0099" not in rejeitados.get("order_id", pd.Series(dtype=str)).values
    assert any(item.order_id == "ord-0099" for item in validos)
