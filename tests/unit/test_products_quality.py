from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.products import (
    REASON_DUPLICATE_PRODUCT_ID,
    validate_products_dataframe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "products_sample.csv", dtype=str, keep_default_na=True
    )


def test_produto_sem_categoria_e_valido() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_products_dataframe(dataframe)

    ids_validos = {p.product_id for p in validos}
    assert "prod-0002" in ids_validos
    produto = next(p for p in validos if p.product_id == "prod-0002")
    assert produto.product_category_name is None


def test_peso_negativo_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_products_dataframe(dataframe)

    linha = rejeitados[rejeitados["product_id"] == "prod-0003"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_product_id_duplicado_e_rejeitado_em_ambas_ocorrencias() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_products_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["product_id"] == "prod-0004"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_PRODUCT_ID).all()


def test_produto_valido_com_todas_dimensoes() -> None:
    dataframe = _carregar_amostra()

    validos, _ = validate_products_dataframe(dataframe)

    produto = next(p for p in validos if p.product_id == "prod-0001")
    assert produto.product_weight_g == 500
    assert produto.product_category_name == "beleza_saude"
