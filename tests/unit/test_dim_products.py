from __future__ import annotations

import pandas as pd

from src.loading.dim_products import build_dim_products


def _products_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_id": "prod-1",
                "product_category_name": "beleza_saude",
                "product_name_lenght": 40.0,
                "product_description_lenght": 287.0,
                "product_photos_qty": 1.0,
            },
            {
                "product_id": "prod-2",
                "product_category_name": None,
                "product_name_lenght": 40.0,
                "product_description_lenght": 287.0,
                "product_photos_qty": 1.0,
            },
            {
                "product_id": "prod-3",
                "product_category_name": "categoria_sem_traducao",
                "product_name_lenght": 40.0,
                "product_description_lenght": 287.0,
                "product_photos_qty": 1.0,
            },
            {
                "product_id": "prod-4",
                "product_category_name": "beleza_saude",
                "product_name_lenght": None,
                "product_description_lenght": None,
                "product_photos_qty": None,
            },
        ]
    )


def _translation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_category_name": "beleza_saude",
                "product_category_name_english": "health_beauty",
            }
        ]
    )


def test_categoria_e_traduzida_para_ingles() -> None:
    dim_products = build_dim_products(_products_df(), _translation_df())

    linha = dim_products[dim_products["product_id"] == "prod-1"].iloc[0]
    assert linha["product_category_name_english"] == "health_beauty"


def test_produto_sem_categoria_nao_e_descartado() -> None:
    dim_products = build_dim_products(_products_df(), _translation_df())

    linha = dim_products[dim_products["product_id"] == "prod-2"]
    assert len(linha) == 1
    assert pd.isna(linha.iloc[0]["product_category_name_english"])


def test_categoria_sem_traducao_disponivel_fica_nula_sem_descartar() -> None:
    dim_products = build_dim_products(_products_df(), _translation_df())

    linha = dim_products[dim_products["product_id"] == "prod-3"].iloc[0]
    assert pd.isna(linha["product_category_name_english"])


def test_mantem_uma_linha_por_produto() -> None:
    dim_products = build_dim_products(_products_df(), _translation_df())

    assert len(dim_products) == 4
    assert dim_products["product_id"].is_unique


def test_medidas_numericas_ausentes_viram_none_nao_nan() -> None:
    """Regressão: dataset real do Olist tem 610 produtos sem essas 3 colunas.
    NaN (não None) nesses campos causa 'integer out of range' no Postgres
    (cast implícito float8->integer), não um erro de sintaxe — só era
    detectável rodando a carga de verdade contra Postgres, não em memória."""
    dim_products = build_dim_products(_products_df(), _translation_df())

    linha = dim_products[dim_products["product_id"] == "prod-4"].iloc[0]
    assert linha["product_name_lenght"] is None
    assert linha["product_description_lenght"] is None
    assert linha["product_photos_qty"] is None


def test_medidas_numericas_presentes_viram_int_puro() -> None:
    dim_products = build_dim_products(_products_df(), _translation_df())

    linha = dim_products[dim_products["product_id"] == "prod-1"].iloc[0]
    assert linha["product_name_lenght"] == 40
    assert isinstance(linha["product_name_lenght"], int)
