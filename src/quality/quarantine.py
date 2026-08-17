"""Escrita de registros rejeitados na área de quarentena (RF04 da spec)."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def write_rejected(
    rejected_df: pd.DataFrame,
    quarantine_dir: Path,
    entity_name: str,
    batch_date: date,
) -> Path | None:
    """Grava os registros rejeitados em `quarantine_dir/entity_name/batch_date.csv`.

    Retorna o path do arquivo escrito, ou None se não havia nada a rejeitar
    (evita poluir a quarentena com arquivos vazios).
    """
    if rejected_df.empty:
        logger.info(
            "quarentena_vazia", extra={"entidade": entity_name, "data": str(batch_date)}
        )
        return None

    destino_dir = quarantine_dir / entity_name
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{batch_date.isoformat()}.csv"

    rejected_df.to_csv(destino, index=False)

    logger.warning(
        "registros_em_quarentena",
        extra={
            "entidade": entity_name,
            "data": str(batch_date),
            "linhas": len(rejected_df),
            "destino": str(destino),
        },
    )
    return destino
