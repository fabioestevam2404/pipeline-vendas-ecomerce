from __future__ import annotations

import pandas as pd
import pytest

from src.exceptions import SchemaValidationError
from src.ingestion.schema_validator import validate_schema
from src.models.schemas import ORDERS_EXPECTED_COLUMNS


def test_schema_valido_nao_levanta_excecao() -> None:
    dataframe = pd.DataFrame(columns=ORDERS_EXPECTED_COLUMNS)
    validate_schema(dataframe, ORDERS_EXPECTED_COLUMNS)  # não deve levantar


def test_coluna_faltante_levanta_schema_validation_error() -> None:
    colunas_incompletas = [c for c in ORDERS_EXPECTED_COLUMNS if c != "order_status"]
    dataframe = pd.DataFrame(columns=colunas_incompletas)

    with pytest.raises(SchemaValidationError, match="colunas faltantes"):
        validate_schema(dataframe, ORDERS_EXPECTED_COLUMNS)


def test_coluna_inesperada_levanta_schema_validation_error() -> None:
    colunas_com_extra = [*ORDERS_EXPECTED_COLUMNS, "coluna_nao_prevista"]
    dataframe = pd.DataFrame(columns=colunas_com_extra)

    with pytest.raises(SchemaValidationError, match="colunas inesperadas"):
        validate_schema(dataframe, ORDERS_EXPECTED_COLUMNS)
