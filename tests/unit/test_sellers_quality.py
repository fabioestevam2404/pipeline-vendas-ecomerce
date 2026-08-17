from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.sellers import REASON_DUPLICATE_SELLER_ID, validate_sellers_dataframe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "sellers_sample.csv", dtype=str, keep_default_na=True
    )


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_sellers_dataframe(dataframe)

    ids_validos = {v.seller_id for v in validos}
    assert ids_validos == {"seller-0001", "seller-0002"}


def test_uf_invalida_e_rejeitada() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_sellers_dataframe(dataframe)

    linha = rejeitados[rejeitados["seller_id"] == "seller-0003"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_seller_id_duplicado_e_rejeitado_em_ambas_ocorrencias() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_sellers_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["seller_id"] == "seller-0004"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_SELLER_ID).all()
