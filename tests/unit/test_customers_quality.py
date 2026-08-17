from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.quality.customers import (
    REASON_DUPLICATE_CUSTOMER_ID,
    validate_customers_dataframe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar_amostra() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURES_DIR / "customers_sample.csv", dtype=str, keep_default_na=True
    )


def test_registros_validos_sao_convertidos_corretamente() -> None:
    dataframe = _carregar_amostra()

    validos, _rejeitados = validate_customers_dataframe(dataframe)

    ids_validos = {registro.customer_id for registro in validos}
    assert ids_validos == {"cust-0001", "cust-0002", "cust-0003"}


def test_uf_invalida_e_rejeitada() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_customers_dataframe(dataframe)

    linha = rejeitados[rejeitados["customer_id"] == "cust-0004"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_customer_unique_id_ausente_e_rejeitado() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_customers_dataframe(dataframe)

    linha = rejeitados[rejeitados["customer_id"] == "cust-0005"].iloc[0]
    assert "falha de validação" in linha["motivo_rejeicao"]


def test_customer_id_duplicado_e_rejeitado_em_ambas_ocorrencias() -> None:
    dataframe = _carregar_amostra()

    _, rejeitados = validate_customers_dataframe(dataframe)

    duplicados = rejeitados[rejeitados["customer_id"] == "cust-0006"]
    assert len(duplicados) == 2
    assert (duplicados["motivo_rejeicao"] == REASON_DUPLICATE_CUSTOMER_ID).all()


def test_uf_e_normalizada_para_maiusculas() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "customer_id": "cust-x",
                "customer_unique_id": "uniq-x",
                "customer_zip_code_prefix": "12345",
                "customer_city": "sao paulo",
                "customer_state": "sp",
            }
        ]
    )

    validos, _ = validate_customers_dataframe(dataframe)

    assert validos[0].customer_state == "SP"
