"""Leitura de arquivos da landing zone.

Responsabilidade única: ler o arquivo em um DataFrame. Não faz validação de
schema nem de qualidade — isso é responsabilidade de `ingestion.schema_validator`
e `quality.rules`, respectivamente (ver docs/ai/project-context.md).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.exceptions import IngestionError

logger = logging.getLogger(__name__)


def read_csv_file(file_path: Path) -> pd.DataFrame:
    """Lê um arquivo CSV da landing zone como DataFrame de strings.

    Todas as colunas são lidas como string (dtype=str) propositalmente: a
    conversão de tipo (datas, números) acontece na etapa de validação/schema,
    onde os erros de conversão podem ser tratados linha a linha em vez de
    derrubar a leitura do arquivo inteiro.

    Levanta IngestionError (fatal para este arquivo) se o arquivo não existir
    ou não puder ser parseado como CSV.
    """
    if not file_path.exists():
        raise IngestionError(f"Arquivo não encontrado: {file_path}")

    try:
        dataframe = pd.read_csv(file_path, dtype=str, keep_default_na=True)
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise IngestionError(f"Falha ao parsear {file_path}: {exc}") from exc

    logger.info(
        "arquivo_lido",
        extra={"arquivo": file_path.name, "linhas": len(dataframe)},
    )
    return dataframe
