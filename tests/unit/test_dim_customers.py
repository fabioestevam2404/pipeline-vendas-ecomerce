from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.loading.dim_customers import build_dim_customers

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _customers_validos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "customer_id": "cust-0001",
                "customer_unique_id": "uniq-0001",
                "customer_zip_code_prefix": "14409",
                "customer_city": "franca",
                "customer_state": "SP",
            },
            {
                "customer_id": "cust-0002",
                "customer_unique_id": "uniq-0002",
                "customer_zip_code_prefix": "9790",
                "customer_city": "sao bernardo do campo",
                "customer_state": "SP",
            },
            {
                # CEP que não existe no dataset de geolocalização de amostra.
                "customer_id": "cust-0099",
                "customer_unique_id": "uniq-0099",
                "customer_zip_code_prefix": "89254",
                "customer_city": "jaragua do sul",
                "customer_state": "SC",
            },
        ]
    )


def _geolocation() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "geolocation_sample.csv")


def test_dim_customers_enriquece_com_lat_lng_medios() -> None:
    dim = build_dim_customers(_customers_validos(), _geolocation())

    linha = dim[dim["customer_id"] == "cust-0001"].iloc[0]
    # zip 14409 tem 2 linhas na amostra de geolocation; média deve ser calculada.
    assert round(linha["geolocation_lat"], 4) == round((-20.509897 + -20.510000) / 2, 4)


def test_dim_customers_mantem_uma_linha_por_cliente() -> None:
    dim = build_dim_customers(_customers_validos(), _geolocation())

    assert len(dim) == len(_customers_validos())
    assert dim["customer_id"].is_unique


def test_cliente_sem_geolocalizacao_nao_e_descartado() -> None:
    dim = build_dim_customers(_customers_validos(), _geolocation())

    linha = dim[dim["customer_id"] == "cust-0099"]
    assert len(linha) == 1
    assert pd.isna(linha.iloc[0]["geolocation_lat"])
