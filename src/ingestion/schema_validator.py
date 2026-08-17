"""Validação de schema (RF02 da spec): colunas obrigatórias e nomes exatos.

Esta etapa valida a ESTRUTURA do arquivo (colunas certas, presentes), não o
CONTEÚDO das linhas — isso é responsabilidade de `quality.rules` (RF03).
"""

from __future__ import annotations

import logging

import pandas as pd

from src.exceptions import SchemaValidationError

logger = logging.getLogger(__name__)


def validate_schema(dataframe: pd.DataFrame, expected_columns: list[str]) -> None:
    """Valida que o DataFrame contém exatamente as colunas esperadas.

    Falha tanto para colunas faltantes quanto para colunas inesperadas: um
    schema alterado silenciosamente na origem (RF da spec, seção "Casos de erro
    e borda") deve ser detectado explicitamente, não ignorado.

    Levanta SchemaValidationError (fatal para este arquivo) em caso de
    divergência.
    """
    colunas_recebidas = set(dataframe.columns)
    colunas_esperadas = set(expected_columns)

    faltantes = colunas_esperadas - colunas_recebidas
    inesperadas = colunas_recebidas - colunas_esperadas

    if faltantes or inesperadas:
        partes_erro = []
        if faltantes:
            partes_erro.append(f"colunas faltantes: {sorted(faltantes)}")
        if inesperadas:
            partes_erro.append(f"colunas inesperadas: {sorted(inesperadas)}")
        mensagem = "; ".join(partes_erro)
        logger.error("schema_invalido", extra={"detalhe": mensagem})
        raise SchemaValidationError(f"Schema inválido: {mensagem}")

    logger.info("schema_validado", extra={"colunas": expected_columns})
