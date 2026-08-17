from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Engine, text

from src.loading.dim_customers import build_dim_customers
from src.loading.dim_pagamento import (
    build_dim_pagamento,
    resolve_review_score_por_pedido,
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


def _customers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "customer_id": "cust-0001",
                "customer_unique_id": "uniq-0001",
                "customer_zip_code_prefix": "14409",
                "customer_city": "franca",
                "customer_state": "SP",
            },
            {
                "customer_id": "cust-0002",
                "customer_unique_id": "uniq-0002",
                "customer_zip_code_prefix": "9790",
                "customer_city": "sao bernardo do campo",
                "customer_state": "SP",
            },
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
            },
            {
                "geolocation_zip_code_prefix": 13023,
                "geolocation_lat": -22.9,
                "geolocation_lng": -47.06,
                "geolocation_city": "campinas",
                "geolocation_state": "SP",
            },
        ]
    )


def _products_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_id": "prod-0001",
                "product_category_name": "beleza_saude",
                "product_name_lenght": 40,
                "product_description_lenght": 500,
                "product_photos_qty": 2,
                "product_weight_g": 500.0,
                "product_length_cm": 20.0,
                "product_height_cm": 10.0,
                "product_width_cm": 15.0,
            },
            {
                "product_id": "prod-0002",
                "product_category_name": "informatica_acessorios",
                "product_name_lenght": 35,
                "product_description_lenght": 300,
                "product_photos_qty": 1,
                "product_weight_g": 800.0,
                "product_length_cm": 25.0,
                "product_height_cm": 12.0,
                "product_width_cm": 18.0,
            },
        ]
    )


def _translation_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_category_name": "beleza_saude",
                "product_category_name_english": "health_beauty",
            },
            {
                "product_category_name": "informatica_acessorios",
                "product_category_name_english": "computers_accessories",
            },
        ]
    )


def _sellers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "seller_id": "seller-0001",
                "seller_zip_code_prefix": "13023",
                "seller_city": "campinas",
                "seller_state": "SP",
            }
        ]
    )


def _orders_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-0001",
                "customer_id": "cust-0001",
                "order_purchase_timestamp": "2017-05-10 10:00:00",
            },
            {
                "order_id": "ord-0002",
                "customer_id": "cust-0002",
                "order_purchase_timestamp": "2017-05-11 08:00:00",
            },
        ]
    )


def _order_items_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-0001",
                "order_item_id": 1,
                "product_id": "prod-0001",
                "seller_id": "seller-0001",
                "price": 100.0,
                "freight_value": 10.0,
            },
            {
                "order_id": "ord-0002",
                "order_item_id": 1,
                "product_id": "prod-0002",
                "seller_id": "seller-0001",
                "price": 50.0,
                "freight_value": 5.0,
            },
        ]
    )


def _payments_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-0001",
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 3,
                "payment_value": 110.0,
            },
            {
                "order_id": "ord-0002",
                "payment_sequential": 1,
                "payment_type": "boleto",
                "payment_installments": 1,
                "payment_value": 55.0,
            },
        ]
    )


def _reviews_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-0001",
                "review_score": 5,
                "review_creation_date": "2017-05-16 10:00:00",
            }
        ]
    )


def _carregar_todas_dimensoes(mart_engine: Engine) -> None:
    load_dim_customers_mart(
        mart_engine, build_dim_customers(_customers_df(), _geolocation_df())
    )
    load_dim_tempo_mart(mart_engine, build_dim_tempo(_orders_df()))
    load_dim_products_mart(
        mart_engine, build_dim_products(_products_df(), _translation_df())
    )
    load_dim_sellers_mart(
        mart_engine, build_dim_sellers(_sellers_df(), _geolocation_df())
    )
    load_dim_pagamento_mart(mart_engine, build_dim_pagamento(_payments_df()))


def test_load_dim_customers_mart_persiste_registros(mart_engine: Engine) -> None:
    dim_customers_df = build_dim_customers(_customers_df(), _geolocation_df())

    linhas = load_dim_customers_mart(mart_engine, dim_customers_df)

    assert linhas == 2
    with mart_engine.connect() as conn:
        resultado = conn.execute(
            text(
                "SELECT customer_id, customer_sk FROM mart.dim_customers ORDER BY customer_sk"
            )
        ).fetchall()
    assert len(resultado) == 2
    assert {linha.customer_sk for linha in resultado} == {1, 2}


def test_customer_sk_e_estavel_entre_cargas_repetidas(mart_engine: Engine) -> None:
    dim_customers_df = build_dim_customers(_customers_df(), _geolocation_df())

    load_dim_customers_mart(mart_engine, dim_customers_df)
    with mart_engine.connect() as conn:
        sk_antes = dict(
            conn.execute(
                text("SELECT customer_id, customer_sk FROM mart.dim_customers")
            ).fetchall()
        )

    load_dim_customers_mart(mart_engine, dim_customers_df)
    with mart_engine.connect() as conn:
        sk_depois = dict(
            conn.execute(
                text("SELECT customer_id, customer_sk FROM mart.dim_customers")
            ).fetchall()
        )

    assert sk_antes == sk_depois


def test_load_dim_tempo_mart_nao_duplica_em_recarga(mart_engine: Engine) -> None:
    dim_tempo_df = build_dim_tempo(_orders_df())

    load_dim_tempo_mart(mart_engine, dim_tempo_df)
    load_dim_tempo_mart(mart_engine, dim_tempo_df)

    with mart_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM mart.dim_tempo")).scalar()
    assert total == len(dim_tempo_df)


def test_load_dim_products_mart_traduz_categoria(mart_engine: Engine) -> None:
    dim_products_df = build_dim_products(_products_df(), _translation_df())

    linhas = load_dim_products_mart(mart_engine, dim_products_df)

    assert linhas == 2
    with mart_engine.connect() as conn:
        resultado = conn.execute(
            text(
                "SELECT product_category_name_english FROM mart.dim_products "
                "WHERE product_id = 'prod-0001'"
            )
        ).scalar()
    assert resultado == "health_beauty"


def test_product_sk_e_estavel_entre_cargas_repetidas(mart_engine: Engine) -> None:
    dim_products_df = build_dim_products(_products_df(), _translation_df())

    load_dim_products_mart(mart_engine, dim_products_df)
    with mart_engine.connect() as conn:
        sk_antes = dict(
            conn.execute(
                text("SELECT product_id, product_sk FROM mart.dim_products")
            ).fetchall()
        )

    load_dim_products_mart(mart_engine, dim_products_df)
    with mart_engine.connect() as conn:
        sk_depois = dict(
            conn.execute(
                text("SELECT product_id, product_sk FROM mart.dim_products")
            ).fetchall()
        )

    assert sk_antes == sk_depois


def test_load_dim_sellers_mart_persiste_geolocalizacao(mart_engine: Engine) -> None:
    dim_sellers_df = build_dim_sellers(_sellers_df(), _geolocation_df())

    linhas = load_dim_sellers_mart(mart_engine, dim_sellers_df)

    assert linhas == 1
    with mart_engine.connect() as conn:
        resultado = conn.execute(
            text(
                "SELECT geolocation_city FROM mart.dim_sellers WHERE seller_id = 'seller-0001'"
            )
        ).scalar()
    assert resultado == "campinas"


def test_load_fact_pedidos_mart_resolve_todas_as_sk(mart_engine: Engine) -> None:
    _carregar_todas_dimensoes(mart_engine)
    reviews_por_pedido = resolve_review_score_por_pedido(_reviews_df())

    linhas = load_fact_pedidos_mart(
        mart_engine,
        _orders_df(),
        _order_items_df(),
        reviews_por_pedido,
        date(2017, 5, 10),
    )

    assert linhas == 2
    with mart_engine.connect() as conn:
        resultado = conn.execute(text("""
                SELECT f.order_id, c.customer_id, p.product_id, s.seller_id,
                       pg.order_id AS pagamento_order_id, f.review_score
                FROM mart.fact_pedidos f
                JOIN mart.dim_customers c ON c.customer_sk = f.customer_sk
                JOIN mart.dim_products p ON p.product_sk = f.produto_sk
                JOIN mart.dim_sellers s ON s.seller_sk = f.vendedor_sk
                JOIN mart.dim_pagamento pg ON pg.pagamento_sk = f.pagamento_sk
                ORDER BY f.order_id
                """)).fetchall()

    assert len(resultado) == 2
    assert resultado[0].order_id == "ord-0001"
    assert resultado[0].customer_id == "cust-0001"
    assert resultado[0].product_id == "prod-0001"
    assert resultado[0].seller_id == "seller-0001"
    assert resultado[0].pagamento_order_id == "ord-0001"
    assert resultado[0].review_score == 5
    # ord-0002 não tem review na amostra -> nulo, sem quebrar a carga.
    assert resultado[1].review_score is None


def test_fact_pedidos_mart_sem_dimensoes_carregadas_nao_persiste_nada(
    mart_engine: Engine,
) -> None:
    reviews_por_pedido = resolve_review_score_por_pedido(_reviews_df())

    linhas = load_fact_pedidos_mart(
        mart_engine,
        _orders_df(),
        _order_items_df(),
        reviews_por_pedido,
        date(2017, 5, 10),
    )

    assert linhas == 0
    with mart_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM mart.fact_pedidos")).scalar()
    assert total == 0


def test_recarregar_fact_pedidos_no_mesmo_item_atualiza_em_vez_de_duplicar(
    mart_engine: Engine,
) -> None:
    _carregar_todas_dimensoes(mart_engine)
    reviews_por_pedido = resolve_review_score_por_pedido(_reviews_df())

    load_fact_pedidos_mart(
        mart_engine,
        _orders_df(),
        _order_items_df(),
        reviews_por_pedido,
        date(2017, 5, 10),
    )
    load_fact_pedidos_mart(
        mart_engine,
        _orders_df(),
        _order_items_df(),
        reviews_por_pedido,
        date(2017, 5, 11),
    )

    with mart_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM mart.fact_pedidos")).scalar()
        batch_date = conn.execute(
            text("SELECT batch_date FROM mart.fact_pedidos WHERE order_id = 'ord-0001'")
        ).scalar()

    assert total == 2
    assert batch_date == date(2017, 5, 11)
