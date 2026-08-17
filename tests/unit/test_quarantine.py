from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.quality.quarantine import write_rejected


def test_grava_arquivo_de_quarentena_com_registros_rejeitados(tmp_path: Path) -> None:
    rejeitados = pd.DataFrame(
        [{"order_id": "ord-0003", "motivo_rejeicao": "falha de validação"}]
    )

    destino = write_rejected(rejeitados, tmp_path, "orders", date(2017, 7, 2))

    assert destino is not None
    assert destino.exists()
    assert destino == tmp_path / "orders" / "2017-07-02.csv"
    conteudo = pd.read_csv(destino)
    assert conteudo.iloc[0]["order_id"] == "ord-0003"


def test_nao_grava_arquivo_quando_nao_ha_rejeitados(tmp_path: Path) -> None:
    rejeitados_vazio = pd.DataFrame()

    destino = write_rejected(rejeitados_vazio, tmp_path, "orders", date(2017, 7, 2))

    assert destino is None
    assert not (tmp_path / "orders").exists()
