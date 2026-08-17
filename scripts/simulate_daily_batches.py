"""Simula a chegada diária dos arquivos do dataset Olist (ADR-002).

O dataset Olist é histórico e estático (pedidos 2016-2018) — não chega novo
todo dia de verdade. Este script particiona o dataset bruto por data para
simular chegadas diárias, permitindo exercitar o pipeline (idempotência,
reprocessamento, batch incremental) como se fosse produção real.

Estratégia de particionamento:
- Entidades TRANSACIONAIS (orders, customers, order_items, order_payments,
  order_reviews): particionadas por data, uma em `order_purchase_timestamp`
  (para orders) ou resolvida via join com orders (para as demais, que não
  têm data própria mas pertencem a um pedido específico).
- Entidades de REFERÊNCIA (products, sellers, geolocation,
  category_translation): não pertencem a um pedido específico — um produto
  não "acontece" numa data. Chegam como snapshot completo, uma única vez, na
  subpasta `reference/` da landing zone — não fica particionado por dia.

Uso:
    python -m scripts.simulate_daily_batches
    python -m scripts.simulate_daily_batches --start-date 2017-01-01 --end-date 2017-01-31
    python -m scripts.simulate_daily_batches --dry-run
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.config import Settings, load_settings
from src.raw_filenames import RAW_FILENAMES, REFERENCE_ENTITIES

logger = logging.getLogger(__name__)


def _ler_bruto(entidade: str, raw_data_dir: Path) -> pd.DataFrame:
    """Lê um arquivo bruto do Kaggle a partir do nome lógico da entidade."""
    caminho = raw_data_dir / RAW_FILENAMES[entidade]
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo bruto não encontrado: {caminho}. Baixe o dataset com "
            f"'kaggle datasets download -d olistbr/brazilian-ecommerce "
            f"-p {raw_data_dir} --unzip' (ver README.md)."
        )
    return pd.read_csv(caminho, dtype=str, keep_default_na=True)


def _mapa_pedido_para_data(orders_df: pd.DataFrame) -> pd.Series:
    """Retorna um mapa order_id -> data (sem hora) de order_purchase_timestamp."""
    datas = pd.to_datetime(orders_df["order_purchase_timestamp"]).dt.date
    return pd.Series(datas.values, index=orders_df["order_id"])


def _escrever_particionado(
    dataframe: pd.DataFrame, entidade: str, landing_zone_dir: Path, dry_run: bool
) -> dict[date, int]:
    """Escreve um DataFrame já com coluna `_data_simulada` particionado por dia.

    Retorna um resumo {data: quantidade de linhas} para logging/relatório.
    """
    resumo: dict[date, int] = {}
    destino_dir = landing_zone_dir / entidade

    for data_simulada, grupo in dataframe.groupby("_data_simulada"):
        grupo_sem_coluna_auxiliar = grupo.drop(columns=["_data_simulada"])
        resumo[data_simulada] = len(grupo_sem_coluna_auxiliar)

        if dry_run:
            continue

        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / f"{data_simulada.isoformat()}.csv"
        grupo_sem_coluna_auxiliar.to_csv(destino, index=False)

    return resumo


def _particionar_orders(
    raw_data_dir: Path,
    landing_zone_dir: Path,
    dry_run: bool,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[pd.DataFrame, dict[date, int]]:
    orders_df = _ler_bruto("orders", raw_data_dir)
    orders_df["_data_simulada"] = pd.to_datetime(
        orders_df["order_purchase_timestamp"]
    ).dt.date

    if start_date is not None:
        orders_df = orders_df[orders_df["_data_simulada"] >= start_date]
    if end_date is not None:
        orders_df = orders_df[orders_df["_data_simulada"] <= end_date]

    resumo = _escrever_particionado(orders_df, "orders", landing_zone_dir, dry_run)
    return orders_df.drop(columns=["_data_simulada"]), resumo


def _particionar_via_order_id(
    entidade: str,
    coluna_pedido: str,
    mapa_pedido_data: pd.Series,
    raw_data_dir: Path,
    landing_zone_dir: Path,
    dry_run: bool,
) -> dict[date, int]:
    """Particiona uma entidade sem data própria, via join com o mapa de pedidos."""
    dataframe = _ler_bruto(entidade, raw_data_dir)
    dataframe["_data_simulada"] = dataframe[coluna_pedido].map(mapa_pedido_data)

    sem_pedido_correspondente = dataframe["_data_simulada"].isna().sum()
    if sem_pedido_correspondente:
        logger.warning(
            "linhas_sem_pedido_correspondente",
            extra={"entidade": entidade, "quantidade": int(sem_pedido_correspondente)},
        )
    dataframe = dataframe.dropna(subset=["_data_simulada"])

    return _escrever_particionado(dataframe, entidade, landing_zone_dir, dry_run)


def _copiar_referencia_completa(
    entidade: str, raw_data_dir: Path, landing_zone_dir: Path, dry_run: bool
) -> int:
    """Copia uma entidade de referência inteira, sem particionar por dia."""
    dataframe = _ler_bruto(entidade, raw_data_dir)
    if not dry_run:
        destino_dir = landing_zone_dir / "reference"
        destino_dir.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(destino_dir / f"{entidade}.csv", index=False)
    return len(dataframe)


def simulate_daily_batches(
    settings: Settings,
    start_date: date | None = None,
    end_date: date | None = None,
    dry_run: bool = False,
) -> dict[str, dict]:
    """Particiona o dataset bruto simulando chegadas diárias na landing zone.

    Retorna um relatório por entidade: {entidade: {data: linhas}} para as
    transacionais, ou {entidade: {"referencia": linhas}} para as de referência.
    """
    relatorio: dict[str, dict] = {}

    orders_df, resumo_orders = _particionar_orders(
        settings.raw_data_dir, settings.landing_zone_dir, dry_run, start_date, end_date
    )
    relatorio["orders"] = resumo_orders

    mapa_pedido_data = _mapa_pedido_para_data(orders_df)

    # customers não tem order_id, mas cada customer_id pertence a exatamente
    # um pedido neste dataset — reaproveita o mesmo helper de particionamento
    # via join, só que mapeando por customer_id -> data do pedido correspondente.
    mapa_cliente_data = pd.Series(
        orders_df["order_id"].map(mapa_pedido_data).values,
        index=orders_df["customer_id"].values,
    )
    relatorio["customers"] = _particionar_via_order_id(
        "customers",
        "customer_id",
        mapa_cliente_data,
        settings.raw_data_dir,
        settings.landing_zone_dir,
        dry_run,
    )

    for entidade, coluna in (
        ("order_items", "order_id"),
        ("order_payments", "order_id"),
        ("order_reviews", "order_id"),
    ):
        relatorio[entidade] = _particionar_via_order_id(
            entidade,
            coluna,
            mapa_pedido_data,
            settings.raw_data_dir,
            settings.landing_zone_dir,
            dry_run,
        )

    for entidade in REFERENCE_ENTITIES:
        linhas = _copiar_referencia_completa(
            entidade, settings.raw_data_dir, settings.landing_zone_dir, dry_run
        )
        relatorio[entidade] = {"referencia_completa": linhas}

    logger.info("simulacao_concluida", extra={"dry_run": dry_run})
    return relatorio


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=str, default=None, help="AAAA-MM-DD")
    parser.add_argument("--end-date", type=str, default=None, help="AAAA-MM-DD")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não escreve arquivos, só mostra o que seria gerado.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    settings = load_settings()

    # Datas vêm de --start-date/--end-date como strings AAAA-MM-DD sem
    # timezone (argumento de linha de comando, não um timestamp de sistema) —
    # naive é o tipo correto aqui, não um descuido.
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()  # noqa: DTZ007
        if args.start_date
        else None
    )
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date()  # noqa: DTZ007
        if args.end_date
        else None
    )

    relatorio = simulate_daily_batches(settings, start_date, end_date, args.dry_run)

    for entidade, resumo in relatorio.items():
        total = sum(resumo.values()) if resumo else 0
        print(f"{entidade}: {len(resumo)} arquivo(s), {total} linha(s) no total")


if __name__ == "__main__":
    main()
