"""Construção de fato_pedidos (RF06 da spec), granularidade: um item de pedido.

Junta `orders` + `order_items`, resolvendo as quatro chaves substitutas do
fato: `customer_sk` (via dim_customers), `produto_sk` (via dim_products),
`vendedor_sk` (via dim_sellers) e `date_sk` (via dim_tempo). Ver
docs/specs/SPEC-001-pipeline-vendas.md, seção "Contratos de dados".
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FACT_PEDIDOS_COLUMNS = [
    "order_id",
    "order_item_id",
    "customer_sk",
    "produto_sk",
    "vendedor_sk",
    "date_sk",
    "pagamento_sk",
    "valor_item",
    "valor_frete",
    "review_score",
]


def _resolver_chave(
    dataframe: pd.DataFrame,
    dim_df: pd.DataFrame,
    dim_colunas: list[str],
    coluna_join: str,
    nome_sk: str,
    nome_log: str,
) -> pd.DataFrame:
    """Resolve uma chave substituta via merge com a dimensão, com log de perdas.

    Helper interno para não repetir o padrão merge -> contar nulos -> logar ->
    dropar, que se repete para as quatro dimensões do fato.
    """
    resultado = dataframe.merge(dim_df[dim_colunas], on=coluna_join, how="left")
    sem_resolucao = resultado[nome_sk].isna().sum()
    if sem_resolucao:
        logger.warning(nome_log, extra={"quantidade": int(sem_resolucao)})
    return resultado.dropna(subset=[nome_sk])


def build_fact_pedidos(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    dim_customers_df: pd.DataFrame,
    dim_tempo_df: pd.DataFrame,
    dim_products_df: pd.DataFrame,
    dim_sellers_df: pd.DataFrame,
    dim_pagamento_df: pd.DataFrame,
    reviews_por_pedido_df: pd.DataFrame,
) -> pd.DataFrame:
    """Constrói fato_pedidos a partir das entidades e dimensões já validadas.

    Todos os DataFrames de entrada devem conter apenas registros já validados
    pela camada de qualidade (`src/quality/*`) — esta função não valida dados,
    apenas junta e resolve chaves substitutas.

    `dim_pagamento_df` e `reviews_por_pedido_df` DEVEM estar no grão de
    PEDIDO (uma linha por `order_id`) — ver `src/loading/dim_pagamento.py`
    para o porquê: juntar dados no grão de pedido+parcela ou pedido+review
    diretamente no fato (grão de item) causaria fan-out e inflaria métricas.

    Itens cujo `order_id` não existe em `orders_df`, ou cujas chaves
    (cliente, data, produto, vendedor, pagamento) não resolvem contra as
    respectivas dimensões, são descartados com um aviso registrado — não
    interrompem a construção do fato (ver docs/specs, "Disponibilidade e
    recuperação"). `review_score` é EXCEÇÃO: nem todo pedido tem review
    (cliente pode não ter respondido a pesquisa ainda), então fica nulo em
    vez de descartar a linha.
    """
    itens_com_pedido = order_items_df.merge(
        orders_df[["order_id", "customer_id", "order_purchase_timestamp"]],
        on="order_id",
        how="inner",
    )
    itens_orfaos = len(order_items_df) - len(itens_com_pedido)
    if itens_orfaos:
        logger.warning(
            "itens_sem_pedido_correspondente", extra={"quantidade": itens_orfaos}
        )

    itens_com_pedido["date"] = pd.to_datetime(
        itens_com_pedido["order_purchase_timestamp"]
    ).dt.normalize()

    fato = _resolver_chave(
        itens_com_pedido,
        dim_customers_df,
        ["customer_sk", "customer_id"],
        "customer_id",
        "customer_sk",
        "itens_sem_customer_sk_resolvido",
    )
    fato = _resolver_chave(
        fato,
        dim_tempo_df,
        ["date_sk", "date"],
        "date",
        "date_sk",
        "itens_sem_date_sk_resolvido",
    )
    fato = _resolver_chave(
        fato,
        dim_products_df,
        ["product_sk", "product_id"],
        "product_id",
        "product_sk",
        "itens_sem_produto_sk_resolvido",
    )
    fato = _resolver_chave(
        fato,
        dim_sellers_df,
        ["seller_sk", "seller_id"],
        "seller_id",
        "seller_sk",
        "itens_sem_vendedor_sk_resolvido",
    )
    fato = _resolver_chave(
        fato,
        dim_pagamento_df,
        ["pagamento_sk", "order_id"],
        "order_id",
        "pagamento_sk",
        "itens_sem_pagamento_sk_resolvido",
    )

    # review_score é opcional por natureza (pedido pode não ter sido avaliado
    # ainda) — LEFT join sem dropar linhas sem review.
    fato = fato.merge(
        reviews_por_pedido_df[["order_id", "review_score"]],
        on="order_id",
        how="left",
    )
    # NaN (numpy) não é aceito diretamente por psycopg2 como NULL — normaliza
    # para None explicitamente. ATENÇÃO: atribuir uma lista Python com None
    # misturado a int de volta a uma coluna sem forçar dtype=object faz o
    # pandas reconverter None -> NaN silenciosamente (reinferência de tipo).
    # Só dtype=object explícito preserva o None de fato.
    fato["review_score"] = pd.Series(
        [int(v) if pd.notna(v) else None for v in fato["review_score"]],
        index=fato.index,
        dtype=object,
    )

    fato = fato.rename(
        columns={
            "price": "valor_item",
            "freight_value": "valor_frete",
            "product_sk": "produto_sk",
            "seller_sk": "vendedor_sk",
        }
    )
    for coluna_sk in (
        "customer_sk",
        "date_sk",
        "produto_sk",
        "vendedor_sk",
        "pagamento_sk",
    ):
        fato[coluna_sk] = fato[coluna_sk].astype(int)

    logger.info(
        "fato_pedidos_construido",
        extra={"linhas": len(fato), "linhas_origem_itens": len(order_items_df)},
    )
    return fato[FACT_PEDIDOS_COLUMNS]
