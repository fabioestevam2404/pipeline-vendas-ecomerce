from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Engine, text

from src.loading.dim_customers import build_dim_customers
from src.loading.dim_pagamento import (
    build_dim_pagamento,
)
from src.loading.dim_products import build_dim_products
from src.loading.dim_sellers import build_dim_sellers
from src.loading.dim_tempo import build_dim_tempo
from src.loading.load_mart import (
    load_dim_customers_mart,
    load_dim_pagamento_mart,
    load_dim_products_mart,
    load_dim_sellers_mart,
    load_dim_tempo_mart,
    load_fact_pedidos_mart,
)
from src.loading.reporting_views import create_reporting_views


def _customers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "customer_id": "cust-1",
                "customer_unique_id": "uniq-1",
                "customer_zip_code_prefix": "14409",
                "customer_city": "franca",
                "customer_state": "SP",
            }
        ]
    )


def _geolocation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "geolocation_zip_code_prefix": 14409,
                "geolocation_lat": -20.5,
                "geolocation_lng": -47.4,
                "geolocation_city": "franca",
                "geolocation_state": "SP",
            }
        ]
    )


def _products_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_id": "prod-1",
                "product_category_name": "beleza_saude",
                "product_name_lenght": 40,
                "product_description_lenght": 500,
                "product_photos_qty": 2,
                "product_weight_g": 500.0,
                "product_length_cm": 20.0,
                "product_height_cm": 10.0,
                "product_width_cm": 15.0,
            }
        ]
    )


def _translation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_category_name": "beleza_saude",
                "product_category_name_english": "health_beauty",
            }
        ]
    )


def _sellers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "seller_id": "seller-1",
                "seller_zip_code_prefix": "14409",
                "seller_city": "franca",
                "seller_state": "SP",
            }
        ]
    )


def _orders_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "customer_id": "cust-1",
                "order_purchase_timestamp": "2017-05-10 10:00:00",
            }
        ]
    )


def _order_items_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "order_item_id": 1,
                "product_id": "prod-1",
                "seller_id": "seller-1",
                "price": 100.0,
                "freight_value": 10.0,
            },
            {
                "order_id": "ord-1",
                "order_item_id": 2,
                "product_id": "prod-1",
                "seller_id": "seller-1",
                "price": 50.0,
                "freight_value": 5.0,
            },
        ]
    )


def _payments_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 2,
                "payment_value": 165.0,
            }
        ]
    )


def test_views_de_consumo_batem_com_os_dados_de_origem(mart_engine: Engine) -> None:
    """Prova o critério de aceitação da spec: 'as métricas de vendas (total,
    por produto, por loja, por período) batem com os dados de origem' —
    valor de origem: 2 itens de ord-1, (100+50) em itens + (10+5) em frete."""
    load_dim_customers_mart(
        mart_engine, build_dim_customers(_customers_df(), _geolocation_df())
    )
    load_dim_products_mart(
        mart_engine, build_dim_products(_products_df(), _translation_df())
    )
    load_dim_sellers_mart(
        mart_engine, build_dim_sellers(_sellers_df(), _geolocation_df())
    )
    load_dim_tempo_mart(mart_engine, build_dim_tempo(_orders_df()))
    load_dim_pagamento_mart(mart_engine, build_dim_pagamento(_payments_df()))

    reviews_vazio = pd.DataFrame(columns=["order_id", "review_score"])
    load_fact_pedidos_mart(
        mart_engine, _orders_df(), _order_items_df(), reviews_vazio, date(2017, 5, 10)
    )

    create_reporting_views(mart_engine)

    with mart_engine.connect() as conn:
        produto = conn.execute(
            text("SELECT * FROM mart.vw_vendas_por_produto WHERE product_id = 'prod-1'")
        ).fetchone()
        vendedor = conn.execute(
            text(
                "SELECT * FROM mart.vw_vendas_por_vendedor WHERE seller_id = 'seller-1'"
            )
        ).fetchone()
        periodo = conn.execute(
            text("SELECT * FROM mart.vw_vendas_por_periodo WHERE date_sk = 20170510")
        ).fetchone()
        resumo = conn.execute(
            text("SELECT * FROM mart.vw_resumo_pedidos WHERE order_id = 'ord-1'")
        ).fetchone()

    # Origem: 2 itens de prod-1, receita 100+50=150, frete 10+5=15.
    assert produto.qtd_itens_vendidos == 2
    assert float(produto.receita_total) == 150.0
    assert float(produto.frete_total) == 15.0

    assert vendedor.qtd_itens_vendidos == 2
    assert float(vendedor.receita_total) == 150.0

    assert periodo.qtd_itens_vendidos == 2
    assert periodo.qtd_pedidos == 1
    assert float(periodo.receita_total) == 150.0

    assert resumo.qtd_itens == 2
    assert float(resumo.valor_total_pedido) == 165.0  # 150 + 15
    assert resumo.forma_pagamento_principal == "credit_card"


def test_views_sao_idempotentes_create_or_replace(mart_engine: Engine) -> None:
    """CREATE OR REPLACE VIEW não deve falhar ao rodar duas vezes seguidas —
    é assim que o pipeline chama isso a cada execução."""
    create_reporting_views(mart_engine)
    create_reporting_views(mart_engine)  # não deve levantar exceção

    with mart_engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM mart.vw_vendas_por_produto")
        ).scalar()
    assert total == 0  # sem dados carregados neste teste, mas a view existe e responde
