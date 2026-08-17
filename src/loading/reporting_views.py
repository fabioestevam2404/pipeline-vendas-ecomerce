"""Views de consumo (schema `mart`), pensadas para conexão de ferramentas de BI
(Power BI, Tableau, Metabase) — RF do critério de aceitação da spec:
"dado o data mart populado, quando o Power BI conecta, as métricas de vendas
(total, por produto, por loja, por período) batem com os dados de origem".

Cada view é uma agregação pronta, evitando que a ferramenta de BI precise
recalcular joins/agregações pesadas a cada refresh — Power BI em modo
DirectQuery se beneficia bastante disso.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_CREATE_VW_VENDAS_POR_PRODUTO = """
CREATE OR REPLACE VIEW mart.vw_vendas_por_produto AS
SELECT
    p.product_sk,
    p.product_id,
    p.product_category_name,
    p.product_category_name_english,
    COUNT(*) AS qtd_itens_vendidos,
    SUM(f.valor_item) AS receita_total,
    SUM(f.valor_frete) AS frete_total,
    AVG(f.valor_item) AS ticket_medio_item
FROM mart.fact_pedidos f
JOIN mart.dim_products p ON p.product_sk = f.produto_sk
GROUP BY p.product_sk, p.product_id, p.product_category_name, p.product_category_name_english
"""

_CREATE_VW_VENDAS_POR_VENDEDOR = """
CREATE OR REPLACE VIEW mart.vw_vendas_por_vendedor AS
SELECT
    s.seller_sk,
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(*) AS qtd_itens_vendidos,
    SUM(f.valor_item) AS receita_total,
    SUM(f.valor_frete) AS frete_total
FROM mart.fact_pedidos f
JOIN mart.dim_sellers s ON s.seller_sk = f.vendedor_sk
GROUP BY s.seller_sk, s.seller_id, s.seller_city, s.seller_state
"""

_CREATE_VW_VENDAS_POR_PERIODO = """
CREATE OR REPLACE VIEW mart.vw_vendas_por_periodo AS
SELECT
    t.date_sk,
    t.date,
    t.ano,
    t.mes,
    t.trimestre,
    t.fim_de_semana,
    COUNT(*) AS qtd_itens_vendidos,
    COUNT(DISTINCT f.order_id) AS qtd_pedidos,
    SUM(f.valor_item) AS receita_total,
    SUM(f.valor_frete) AS frete_total
FROM mart.fact_pedidos f
JOIN mart.dim_tempo t ON t.date_sk = f.date_sk
GROUP BY t.date_sk, t.date, t.ano, t.mes, t.trimestre, t.fim_de_semana
"""

_CREATE_VW_RESUMO_PEDIDOS = """
CREATE OR REPLACE VIEW mart.vw_resumo_pedidos AS
SELECT
    f.order_id,
    c.customer_id,
    c.customer_city,
    c.customer_state,
    t.date AS data_pedido,
    COUNT(*) AS qtd_itens,
    SUM(f.valor_item) AS valor_itens,
    SUM(f.valor_frete) AS valor_frete,
    SUM(f.valor_item) + SUM(f.valor_frete) AS valor_total_pedido,
    MAX(pg.forma_pagamento_principal) AS forma_pagamento_principal,
    MAX(f.review_score) AS review_score
FROM mart.fact_pedidos f
JOIN mart.dim_customers c ON c.customer_sk = f.customer_sk
JOIN mart.dim_tempo t ON t.date_sk = f.date_sk
JOIN mart.dim_pagamento pg ON pg.pagamento_sk = f.pagamento_sk
GROUP BY f.order_id, c.customer_id, c.customer_city, c.customer_state, t.date
"""

_TODAS_AS_VIEWS = [
    ("vw_vendas_por_produto", _CREATE_VW_VENDAS_POR_PRODUTO),
    ("vw_vendas_por_vendedor", _CREATE_VW_VENDAS_POR_VENDEDOR),
    ("vw_vendas_por_periodo", _CREATE_VW_VENDAS_POR_PERIODO),
    ("vw_resumo_pedidos", _CREATE_VW_RESUMO_PEDIDOS),
]


def create_reporting_views(engine: Engine) -> None:
    """Cria (ou substitui) as views de consumo no schema `mart`.

    Idempotente: `CREATE OR REPLACE VIEW` — seguro chamar em toda execução do
    pipeline, depois de `create_mart_schema`. As views refletem sempre o
    estado atual das tabelas — não são materializadas, não precisam de
    refresh separado.
    """
    with engine.begin() as conn:
        for nome, ddl in _TODAS_AS_VIEWS:
            conn.execute(text(ddl))
            logger.info("view_criada", extra={"view": f"mart.{nome}"})
