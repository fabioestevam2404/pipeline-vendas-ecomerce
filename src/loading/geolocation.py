"""Enriquecimento por geolocalização, compartilhado por dim_customers e dim_sellers.

Extraído de `dim_customers.py` ao implementar `dim_sellers.py`, que precisa
exatamente da mesma agregação (CEP -> lat/lng médios, cidade/estado mais
frequente), só que aplicada a `seller_zip_code_prefix` em vez de
`customer_zip_code_prefix`.
"""

from __future__ import annotations

import pandas as pd


def _aggregate_geolocation_by_zip(geolocation_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega o dataset de geolocalização por CEP (zip_code_prefix).

    O dataset bruto tem múltiplas coordenadas por CEP (várias ruas dentro do
    mesmo prefixo). Usamos a média de lat/lng e a cidade/estado mais frequente
    (moda) por CEP, para granularidade de 1 linha por CEP.
    """
    geolocation_df = geolocation_df.copy()
    # Não assume o dtype de entrada: dependendo de como o CSV foi lido (ex.:
    # via read_csv_file, que força dtype=str para todas as colunas — usado
    # nas entidades transacionais que passam por validação Pydantic),
    # lat/lng podem chegar como string. `.mean()` quebra em coluna string
    # ("dtype 'str' does not support operation 'mean'") — bug real, achado
    # rodando a DAG de seed sob Airflow. Convertendo explicitamente aqui,
    # a função fica robusta independente de como o chamador leu o CSV.
    geolocation_df["geolocation_lat"] = pd.to_numeric(geolocation_df["geolocation_lat"])
    geolocation_df["geolocation_lng"] = pd.to_numeric(geolocation_df["geolocation_lng"])

    agrupado = geolocation_df.groupby("geolocation_zip_code_prefix").agg(
        geolocation_lat=("geolocation_lat", "mean"),
        geolocation_lng=("geolocation_lng", "mean"),
        geolocation_city=("geolocation_city", lambda serie: serie.mode().iloc[0]),
        geolocation_state=("geolocation_state", lambda serie: serie.mode().iloc[0]),
    )
    agrupado = agrupado.reset_index()
    # Normaliza o CEP para string: a origem dos DataFrames pode divergir
    # (entidades sempre lidas como string por file_reader; geolocation pode
    # vir de uma leitura numérica), e um merge entre tipos diferentes falha.
    agrupado["geolocation_zip_code_prefix"] = agrupado[
        "geolocation_zip_code_prefix"
    ].astype(str)
    return agrupado


def enrich_with_geolocation(
    entity_df: pd.DataFrame, geolocation_df: pd.DataFrame, zip_column: str
) -> pd.DataFrame:
    """Enriquece `entity_df` com lat/lng/cidade/estado agregados por CEP.

    `zip_column`: nome da coluna de CEP na entidade (ex.:
    `customer_zip_code_prefix` ou `seller_zip_code_prefix`).

    Linhas cujo CEP não existe no dataset de geolocalização recebem lat/lng
    nulos, não são descartadas (falha de enriquecimento não interrompe a
    carga da dimensão — ver docs/specs, "Disponibilidade e recuperação").
    """
    geo_agregado = _aggregate_geolocation_by_zip(geolocation_df)

    enriquecido = (
        entity_df.assign(**{zip_column: entity_df[zip_column].astype(str)})
        .merge(
            geo_agregado,
            how="left",
            left_on=zip_column,
            right_on="geolocation_zip_code_prefix",
            suffixes=("", "_geo"),
        )
        .drop(columns=["geolocation_zip_code_prefix"])
    )
    return enriquecido
