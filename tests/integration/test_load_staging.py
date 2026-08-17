from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Engine, text

from src.loading.load_staging import (
    load_customers_staging,
    load_order_items_staging,
    load_orders_staging,
    load_payments_staging,
    load_products_staging,
    load_reviews_staging,
    load_sellers_staging,
)
from src.models.schemas import (
    CustomerRecord,
    OrderItemRecord,
    OrderRecord,
    PaymentRecord,
    ProductRecord,
    ReviewRecord,
    SellerRecord,
)

# Datas naive (sem tzinfo) são deliberadas: consistentes com o restante do
# projeto, já que o dataset Olist não traz timezone (ver src/models/schemas.py).
_10_MAI_2017_10H = datetime(2017, 5, 10, 10, 0, 0)  # noqa: DTZ001
_10_MAI_2017_12H = datetime(2017, 5, 10, 12, 0, 0)  # noqa: DTZ001
_11_MAI_2017_09H = datetime(2017, 5, 11, 9, 0, 0)  # noqa: DTZ001
_15_MAI_2017_14H = datetime(2017, 5, 15, 14, 0, 0)  # noqa: DTZ001
_20_MAI_2017 = datetime(2017, 5, 20, 0, 0, 0)  # noqa: DTZ001
_12_MAI_2017_10H = datetime(2017, 5, 12, 10, 0, 0)  # noqa: DTZ001


def _pedido_exemplo(order_id: str = "ord-0001") -> OrderRecord:
    return OrderRecord(
        order_id=order_id,
        customer_id="cust-0001",
        order_status="delivered",
        order_purchase_timestamp=_10_MAI_2017_10H,
        order_approved_at=_10_MAI_2017_12H,
        order_delivered_carrier_date=_11_MAI_2017_09H,
        order_delivered_customer_date=_15_MAI_2017_14H,
        order_estimated_delivery_date=_20_MAI_2017,
    )


def test_carrega_pedido_novo_em_staging(engine: Engine) -> None:
    linhas_afetadas = load_orders_staging(
        engine, [_pedido_exemplo()], date(2017, 5, 10)
    )

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT order_id, order_status, batch_date FROM staging.stg_orders")
        ).fetchall()

    assert len(resultado) == 1
    assert resultado[0].order_id == "ord-0001"
    assert resultado[0].order_status == "delivered"
    assert resultado[0].batch_date == date(2017, 5, 10)


def test_recarregar_o_mesmo_order_id_atualiza_em_vez_de_duplicar(
    engine: Engine,
) -> None:
    load_orders_staging(engine, [_pedido_exemplo()], date(2017, 5, 10))

    pedido_atualizado = _pedido_exemplo().model_copy(
        update={"order_status": "canceled"}
    )
    load_orders_staging(engine, [pedido_atualizado], date(2017, 5, 11))

    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT order_id, order_status, batch_date FROM staging.stg_orders")
        ).fetchall()

    # Idempotência (RF07): mesmo order_id reprocessado -> 1 linha, não 2.
    assert len(resultado) == 1
    assert resultado[0].order_status == "canceled"
    assert resultado[0].batch_date == date(2017, 5, 11)


def test_carrega_multiplos_pedidos_de_uma_vez(engine: Engine) -> None:
    pedidos = [_pedido_exemplo("ord-0001"), _pedido_exemplo("ord-0002")]

    linhas_afetadas = load_orders_staging(engine, pedidos, date(2017, 5, 10))

    assert linhas_afetadas == 2
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM staging.stg_orders")).scalar()
    assert total == 2


def test_lista_vazia_nao_executa_insercao(engine: Engine) -> None:
    linhas_afetadas = load_orders_staging(engine, [], date(2017, 5, 10))

    assert linhas_afetadas == 0
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM staging.stg_orders")).scalar()
    assert total == 0


def test_carrega_customers_em_staging(engine: Engine) -> None:
    cliente = CustomerRecord(
        customer_id="cust-0001",
        customer_unique_id="uniq-0001",
        customer_zip_code_prefix="14409",
        customer_city="franca",
        customer_state="SP",
    )

    linhas_afetadas = load_customers_staging(engine, [cliente], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT customer_id, customer_state FROM staging.stg_customers")
        ).fetchall()
    assert resultado[0].customer_state == "SP"


def test_carrega_order_items_com_chave_composta(engine: Engine) -> None:
    item = OrderItemRecord(
        order_id="ord-0001",
        order_item_id=1,
        product_id="prod-0001",
        seller_id="seller-0001",
        shipping_limit_date=_12_MAI_2017_10H,
        price=89.90,
        freight_value=12.50,
    )

    linhas_afetadas = load_order_items_staging(engine, [item], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT order_id, order_item_id, price FROM staging.stg_order_items")
        ).fetchall()
    assert resultado[0].order_id == "ord-0001"
    assert resultado[0].order_item_id == 1
    assert float(resultado[0].price) == 89.90


def test_dois_itens_do_mesmo_pedido_nao_colidem_na_chave_composta(
    engine: Engine,
) -> None:
    itens = [
        OrderItemRecord(
            order_id="ord-0001",
            order_item_id=1,
            product_id="prod-0001",
            seller_id="seller-0001",
            shipping_limit_date=_12_MAI_2017_10H,
            price=89.90,
            freight_value=12.50,
        ),
        OrderItemRecord(
            order_id="ord-0001",
            order_item_id=2,
            product_id="prod-0002",
            seller_id="seller-0002",
            shipping_limit_date=_12_MAI_2017_10H,
            price=45.00,
            freight_value=8.30,
        ),
    ]

    linhas_afetadas = load_order_items_staging(engine, itens, date(2017, 5, 10))

    assert linhas_afetadas == 2
    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM staging.stg_order_items")
        ).scalar()
    assert total == 2


def test_carrega_products_em_staging(engine: Engine) -> None:
    produto = ProductRecord(
        product_id="prod-0001",
        product_category_name="beleza_saude",
        product_weight_g=500,
    )

    linhas_afetadas = load_products_staging(engine, [produto], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT product_id, product_category_name FROM staging.stg_products")
        ).fetchall()
    assert resultado[0].product_category_name == "beleza_saude"


def test_carrega_product_sem_categoria_com_nulo_preservado(engine: Engine) -> None:
    produto = ProductRecord(product_id="prod-0002")

    load_products_staging(engine, [produto], date(2017, 5, 10))

    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT product_category_name FROM staging.stg_products")
        ).scalar()
    assert resultado is None


def test_carrega_sellers_em_staging(engine: Engine) -> None:
    vendedor = SellerRecord(
        seller_id="seller-0001",
        seller_zip_code_prefix="13023",
        seller_city="campinas",
        seller_state="SP",
    )

    linhas_afetadas = load_sellers_staging(engine, [vendedor], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT seller_id, seller_state FROM staging.stg_sellers")
        ).fetchall()
    assert resultado[0].seller_state == "SP"


def test_carrega_payments_em_staging(engine: Engine) -> None:
    pagamento = PaymentRecord(
        order_id="ord-0001",
        payment_sequential=1,
        payment_type="credit_card",
        payment_installments=3,
        payment_value=150.0,
    )

    linhas_afetadas = load_payments_staging(engine, [pagamento], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT order_id, payment_type FROM staging.stg_order_payments")
        ).fetchall()
    assert resultado[0].payment_type == "credit_card"


def test_dois_pagamentos_do_mesmo_pedido_nao_colidem_na_chave_composta(
    engine: Engine,
) -> None:
    pagamentos = [
        PaymentRecord(
            order_id="ord-0001",
            payment_sequential=1,
            payment_type="voucher",
            payment_installments=1,
            payment_value=20.0,
        ),
        PaymentRecord(
            order_id="ord-0001",
            payment_sequential=2,
            payment_type="credit_card",
            payment_installments=2,
            payment_value=80.0,
        ),
    ]

    linhas_afetadas = load_payments_staging(engine, pagamentos, date(2017, 5, 10))

    assert linhas_afetadas == 2
    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM staging.stg_order_payments")
        ).scalar()
    assert total == 2


def test_carrega_reviews_em_staging(engine: Engine) -> None:
    review = ReviewRecord(
        review_id="rev-0001",
        order_id="ord-0001",
        review_score=5,
        review_creation_date=_10_MAI_2017_10H,
    )

    linhas_afetadas = load_reviews_staging(engine, [review], date(2017, 5, 10))

    assert linhas_afetadas == 1
    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT review_id, review_score FROM staging.stg_order_reviews")
        ).fetchall()
    assert resultado[0].review_score == 5


def test_review_sem_resposta_preserva_nulo(engine: Engine) -> None:
    review = ReviewRecord(
        review_id="rev-0002",
        order_id="ord-0002",
        review_score=3,
        review_creation_date=_10_MAI_2017_10H,
    )

    load_reviews_staging(engine, [review], date(2017, 5, 10))

    with engine.connect() as conn:
        resultado = conn.execute(
            text("SELECT review_answer_timestamp FROM staging.stg_order_reviews")
        ).scalar()
    assert resultado is None
