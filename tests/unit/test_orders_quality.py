from __future__ import annotations

from pathlib import Path

from src.ingestion.file_reader import read_csv_file
from src.quality.orders import (
    REASON_DELIVERY_BEFORE_PURCHASE,
    REASON_DUPLICATE_ORDER_ID,
    validate_orders_dataframe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


import pandas as pd


def _carregar_amostra() -> pd.DataFrame:
    return read_csv_file(FIXTURES_DIR / "orders_sample.csv")


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_orders_dataframe(dataframe)

    ids_validos = {registro.order_id for registro in validos}
    # ord-0001 e ord-0002 são os únicos registros sem nenhum problema de qualidade.
    assert ids_validos == {"ord-0001", "ord-0002"}


def test_purchase_timestamp_ausente_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_orders_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0003"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_status_invalido_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_orders_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0004"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_data_estimada_antes_da_compra_e_rejeitada() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_orders_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0005"]
    # ord-0005 deveria ter sido rejeitado (estimativa antes da compra), portanto
    # NÃO deve aparecer na lista de válidos verificada no teste anterior.
    assert not linha.empty
    assert linha.iloc[0]["motivo_rejeicao"] == REASON_DELIVERY_BEFORE_PURCHASE


def test_order_id_duplicado_e_rejeitado_em_ambas_as_ocorrencias() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_orders_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["order_id"] == "ord-0006"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_ORDER_ID).all()


def test_total_de_linhas_rejeitadas_e_validas_bate_com_o_arquivo() -> None:
    dataframe = _carregar_amostra()

    validos, rejeitados = validate_orders_dataframe(dataframe)

    assert len(validos) + len(rejeitados) == len(dataframe)
