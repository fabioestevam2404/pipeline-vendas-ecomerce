from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.payments import (
    REASON_DUPLICATE_PAYMENT_KEY,
    validate_payments_dataframe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "order_payments_sample.csv", dtype=str, keep_default_na=True
    )


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_payments_dataframe(dataframe)

    ids_validos = {p.order_id for p in validos}
    assert ids_validos == {"ord-0001", "ord-0002"}


def test_payment_type_invalido_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_payments_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0003"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_parcelas_negativas_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_payments_dataframe(dataframe)

    linha = rejeitados[rejeitados["order_id"] == "ord-0004"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_chave_composta_duplicada_e_rejeitada() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_payments_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["order_id"] == "ord-0005"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_PAYMENT_KEY).all()
