from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.reviews import REASON_DUPLICATE_REVIEW_ID, validate_reviews_dataframe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "order_reviews_sample.csv", dtype=str, keep_default_na=True
    )


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_reviews_dataframe(dataframe)

    ids_validos = {r.review_id for r in validos}
    assert ids_validos == {"rev-0001", "rev-0002"}


def test_review_score_fora_do_intervalo_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_reviews_dataframe(dataframe)

    linha = rejeitados[rejeitados["review_id"] == "rev-0003"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_review_id_duplicado_e_rejeitado_em_ambas_ocorrencias() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_reviews_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["review_id"] == "rev-0004"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_REVIEW_ID).all()


def test_review_sem_comentario_e_valido() -> None:
    dataframe = _carregar_amostra()

    validos, _ = validate_reviews_dataframe(dataframe)

    review = next(r for r in validos if r.review_id == "rev-0002")
    assert review.review_comment_message is None
    assert review.review_answer_timestamp is None
