from __future__ import annotations

from pathlib import Path

import pytest

from src.exceptions import IngestionError
from src.ingestion.file_reader import read_csv_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_le_arquivo_valido_como_dataframe_de_strings() -> None:
    dataframe = read_csv_file(FIXTURES_DIR / "orders_sample.csv")

    assert len(dataframe) == 7
    # Verifica que os valores são strings Python (o dtype exato varia entre
    # versões do pandas: 'object' ou 'StringDtype', ambos aceitáveis aqui).
    assert all(isinstance(valor, str) for valor in dataframe["order_id"])


def test_arquivo_inexistente_levanta_ingestion_error() -> None:
    with pytest.raises(IngestionError, match="não encontrado"):
        read_csv_file(FIXTURES_DIR / "arquivo_que_nao_existe.csv")
