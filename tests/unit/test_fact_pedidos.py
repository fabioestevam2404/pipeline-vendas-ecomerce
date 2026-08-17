from __future__ import annotations

import pandas as pd

from src.loading.dim_customers import build_dim_customers
from src.loading.dim_pagamento import (
    build_dim_pagamento,
    resolve_review_score_por_pedido,
)
from src.loading.dim_products import build_dim_products
from src.loading.dim_sellers import build_dim_sellers
from src.loading.dim_tempo import build_dim_tempo
from src.loading.fact_pedidos import build_fact_pedidos


def _orders() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "customer_id": "cust-1",
                "order_purchase_timestamp": "2017-05-10 10:00:00",
            },
            {
                "order_id": "ord-2",
                "customer_id": "cust-2",
                "order_purchase_timestamp": "2017-05-11 08:00:00",
            },
        ]
    )


def _order_items() -> pd.DataFrame:
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
                "product_id": "prod-2",
                "seller_id": "seller-1",
                "price": 50.0,
                "freight_value": 5.0,
            },
            {
                # Item órfão: nenhum pedido "ord-999" em _orders().
                "order_id": "ord-999",
                "order_item_id": 1,
                "product_id": "prod-3",
                "seller_id": "seller-2",
                "price": 30.0,
                "freight_value": 3.0,
            },
        ]
    )


def _dim_customers() -> pd.DataFrame:
    customers_df = pd.DataFrame(
        [
            {
                "customer_id": "cust-1",
                "customer_unique_id": "uniq-1",
                "customer_zip_code_prefix": "14409",
                "customer_city": "franca",
                "customer_state": "SP",
            },
            {
                "customer_id": "cust-2",
                "customer_unique_id": "uniq-2",
                "customer_zip_code_prefix": "9790",
                "customer_city": "sao bernardo do campo",
                "customer_state": "SP",
            },
        ]
    )
    geolocation_df = pd.DataFrame(
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
    return build_dim_customers(customers_df, geolocation_df)


def _dim_products() -> pd.DataFrame:
    products_df = pd.DataFrame(
        [
            {
                "product_id": "prod-1",
                "product_category_name": "beleza_saude",
                "product_name_lenght": 40.0,
                "product_description_lenght": 287.0,
                "product_photos_qty": 1.0,
            },
            {
                "product_id": "prod-2",
                "product_category_name": "informatica_acessorios",
                "product_name_lenght": 40.0,
                "product_description_lenght": 287.0,
                "product_photos_qty": 1.0,
            },
        ]
    )
    translation_df = pd.DataFrame(
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
    return build_dim_products(products_df, translation_df)


def _dim_sellers() -> pd.DataFrame:
    sellers_df = pd.DataFrame(
        [
            {
                "seller_id": "seller-1",
                "seller_zip_code_prefix": "13023",
                "seller_city": "campinas",
                "seller_state": "SP",
            }
        ]
    )
    geolocation_df = pd.DataFrame(
        [
            {
                "geolocation_zip_code_prefix": 13023,
                "geolocation_lat": -22.9,
                "geolocation_lng": -47.06,
                "geolocation_city": "campinas",
                "geolocation_state": "SP",
            }
        ]
    )
    return build_dim_sellers(sellers_df, geolocation_df)


def _payments_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_id": "ord-1",
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 3,
                "payment_value": 150.0,
            },
            {
                "order_id": "ord-2",
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
                "order_id": "ord-1",
                "review_score": 5,
                "review_creation_date": "2017-05-16 10:00:00",
            }
        ]
    )


def _build_fato() -> pd.DataFrame:
    return build_fact_pedidos(
        _orders(),
        _order_items(),
        _dim_customers(),
        build_dim_tempo(_orders()),
        _dim_products(),
        _dim_sellers(),
        build_dim_pagamento(_payments_df()),
        resolve_review_score_por_pedido(_reviews_df()),
    )


def test_fato_pedidos_tem_uma_linha_por_item() -> None:
    fato = _build_fato()

    # ord-1 tem 2 itens; ord-2 não tem itens; ord-999 é órfão e é descartado.
    assert len(fato) == 2
    assert set(fato["order_id"]) == {"ord-1"}


def test_fato_pedidos_resolve_customer_sk_corretamente() -> None:
    dim_customers = _dim_customers()
    fato = _build_fato()

    sk_esperado = dim_customers.loc[
        dim_customers["customer_id"] == "cust-1", "customer_sk"
    ].iloc[0]
    assert (fato["customer_sk"] == sk_esperado).all()


def test_fato_pedidos_resolve_date_sk_corretamente() -> None:
    fato = _build_fato()

    assert (fato["date_sk"] == 20170510).all()


def test_fato_pedidos_resolve_produto_sk_e_vendedor_sk() -> None:
    dim_products = _dim_products()
    dim_sellers = _dim_sellers()
    fato = _build_fato()

    produto_sk_esperado = dim_products.loc[
        dim_products["product_id"] == "prod-1", "product_sk"
    ].iloc[0]
    vendedor_sk_esperado = dim_sellers.loc[
        dim_sellers["seller_id"] == "seller-1", "seller_sk"
    ].iloc[0]

    linha_item_1 = fato[fato["order_item_id"] == 1].iloc[0]
    assert linha_item_1["produto_sk"] == produto_sk_esperado
    assert linha_item_1["vendedor_sk"] == vendedor_sk_esperado


def test_fato_pedidos_renomeia_metricas_para_portugues() -> None:
    fato = _build_fato()

    assert set(fato.columns) == {
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
    }
    total_item = fato[fato["order_item_id"] == 1]["valor_item"].iloc[0]
    assert total_item == 100.0


def test_fato_pedidos_resolve_pagamento_sk() -> None:
    dim_pagamento = build_dim_pagamento(_payments_df())
    fato = _build_fato()

    sk_esperado = dim_pagamento.loc[
        dim_pagamento["order_id"] == "ord-1", "pagamento_sk"
    ].iloc[0]
    assert (fato["pagamento_sk"] == sk_esperado).all()


def test_fato_pedidos_traz_review_score_quando_existe() -> None:
    fato = _build_fato()

    assert (fato["review_score"] == 5).all()


def test_fato_pedidos_review_score_nulo_quando_pedido_sem_review() -> None:
    # ord-2 não tem review em _reviews_df(); simula um segundo pedido válido.
    order_items_ord2 = pd.DataFrame(
        [
            {
                "order_id": "ord-2",
                "order_item_id": 1,
                "product_id": "prod-1",
                "seller_id": "seller-1",
                "price": 80.0,
                "freight_value": 8.0,
            }
        ]
    )
    fato = build_fact_pedidos(
        _orders(),
        order_items_ord2,
        _dim_customers(),
        build_dim_tempo(_orders()),
        _dim_products(),
        _dim_sellers(),
        build_dim_pagamento(_payments_df()),
        resolve_review_score_por_pedido(_reviews_df()),
    )

    assert fato.iloc[0]["review_score"] is None


def test_item_orfao_e_descartado_sem_derrubar_a_construcao() -> None:
    fato = _build_fato()

    assert "ord-999" not in set(fato["order_id"])


def test_item_com_produto_nao_resolvido_e_descartado() -> None:
    # order_items com um product_id que não existe em dim_products.
    order_items_com_produto_desconhecido = pd.concat(
        [
            _order_items(),
            pd.DataFrame(
                [
                    {
                        "order_id": "ord-1",
                        "order_item_id": 3,
                        "product_id": "prod-inexistente",
                        "seller_id": "seller-1",
                        "price": 20.0,
                        "freight_value": 2.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    fato = build_fact_pedidos(
        _orders(),
        order_items_com_produto_desconhecido,
        _dim_customers(),
        build_dim_tempo(_orders()),
        _dim_products(),
        _dim_sellers(),
        build_dim_pagamento(_payments_df()),
        resolve_review_score_por_pedido(_reviews_df()),
    )

    assert 3 not in set(fato["order_item_id"])
