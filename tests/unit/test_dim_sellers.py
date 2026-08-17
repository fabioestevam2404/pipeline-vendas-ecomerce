from __future__ import annotations

import pandas as pd

from src.loading.dim_sellers import build_dim_sellers


def _sellers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "seller_id": "seller-1",
                "seller_zip_code_prefix": "13023",
                "seller_city": "campinas",
                "seller_state": "SP",
            },
            {
                # CEP que não existe no dataset de geolocalização de amostra.
                "seller_id": "seller-2",
                "seller_zip_code_prefix": "99999",
                "seller_city": "cidade-fantasma",
                "seller_state": "SP",
            },
        ]
    )


def _geolocation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "geolocation_zip_code_prefix": 13023,
                "geolocation_lat": -22.9,
                "geolocation_lng": -47.06,
                "geolocation_city": "campinas",
                "geolocation_state": "SP",
            }
        ]
    )


def test_dim_sellers_enriquece_com_geolocalizacao() -> None:
    dim_sellers = build_dim_sellers(_sellers_df(), _geolocation_df())

    linha = dim_sellers[dim_sellers["seller_id"] == "seller-1"].iloc[0]
    assert linha["geolocation_lat"] == -22.9


def test_vendedor_sem_geolocalizacao_nao_e_descartado() -> None:
    dim_sellers = build_dim_sellers(_sellers_df(), _geolocation_df())

    linha = dim_sellers[dim_sellers["seller_id"] == "seller-2"]
    assert len(linha) == 1
    assert pd.isna(linha.iloc[0]["geolocation_lat"])


def test_mantem_uma_linha_por_vendedor() -> None:
    dim_sellers = build_dim_sellers(_sellers_df(), _geolocation_df())

    assert len(dim_sellers) == 2
    assert dim_sellers["seller_id"].is_unique
