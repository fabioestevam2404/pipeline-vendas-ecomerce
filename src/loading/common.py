"""Helpers compartilhados pelos módulos de src/loading."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from pydantic import BaseModel


def records_to_dataframe(records: Sequence[BaseModel]) -> pd.DataFrame:
    """Converte uma lista de registros pydantic já validados em DataFrame.

    Usado para levar a saída de `src/quality/*` (listas de registros válidos)
    para as junções feitas em `src/loading/*`, sem reabrir a validação.
    """
    if not records:
        return pd.DataFrame()
    return pd.DataFrame([registro.model_dump() for registro in records])
