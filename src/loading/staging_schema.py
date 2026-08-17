"""Definição das tabelas de staging via SQLAlchemy Core.

Usado tanto por `load_staging.py` (carga) quanto por testes de integração
(criação/limpeza do schema). Cada tabela tem `batch_date` e `loaded_at` para
rastreabilidade (RF08 — logs/auditoria de execução) e chave primária igual à
chave natural da entidade, o que viabiliza a estratégia de idempotência via
UPSERT (RF07 — reprocessar o mesmo arquivo não duplica dados).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    func,
)

STAGING_SCHEMA = "staging"

metadata = MetaData(schema=STAGING_SCHEMA)

stg_orders = Table(
    "stg_orders",
    metadata,
    Column("order_id", String, primary_key=True),
    Column("customer_id", String, nullable=False),
    Column("order_status", String, nullable=False),
    Column("order_purchase_timestamp", DateTime, nullable=False),
    Column("order_approved_at", DateTime, nullable=True),
    Column("order_delivered_carrier_date", DateTime, nullable=True),
    Column("order_delivered_customer_date", DateTime, nullable=True),
    Column("order_estimated_delivery_date", DateTime, nullable=False),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_customers = Table(
    "stg_customers",
    metadata,
    Column("customer_id", String, primary_key=True),
    Column("customer_unique_id", String, nullable=False),
    Column("customer_zip_code_prefix", String, nullable=False),
    Column("customer_city", String, nullable=False),
    Column("customer_state", String, nullable=False),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_order_items = Table(
    "stg_order_items",
    metadata,
    Column("order_id", String, primary_key=True),
    Column("order_item_id", Integer, primary_key=True),
    Column("product_id", String, nullable=False),
    Column("seller_id", String, nullable=False),
    Column("shipping_limit_date", DateTime, nullable=False),
    Column("price", Float, nullable=False),
    Column("freight_value", Float, nullable=False),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_products = Table(
    "stg_products",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("product_category_name", String, nullable=True),
    Column("product_name_lenght", Integer, nullable=True),
    Column("product_description_lenght", Integer, nullable=True),
    Column("product_photos_qty", Integer, nullable=True),
    Column("product_weight_g", Float, nullable=True),
    Column("product_length_cm", Float, nullable=True),
    Column("product_height_cm", Float, nullable=True),
    Column("product_width_cm", Float, nullable=True),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_sellers = Table(
    "stg_sellers",
    metadata,
    Column("seller_id", String, primary_key=True),
    Column("seller_zip_code_prefix", String, nullable=False),
    Column("seller_city", String, nullable=False),
    Column("seller_state", String, nullable=False),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_order_payments = Table(
    "stg_order_payments",
    metadata,
    Column("order_id", String, primary_key=True),
    Column("payment_sequential", Integer, primary_key=True),
    Column("payment_type", String, nullable=False),
    Column("payment_installments", Integer, nullable=False),
    Column("payment_value", Float, nullable=False),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

stg_order_reviews = Table(
    "stg_order_reviews",
    metadata,
    Column("review_id", String, primary_key=True),
    Column("order_id", String, nullable=False),
    Column("review_score", Integer, nullable=False),
    Column("review_comment_title", String, nullable=True),
    Column("review_comment_message", String, nullable=True),
    Column("review_creation_date", DateTime, nullable=False),
    Column("review_answer_timestamp", DateTime, nullable=True),
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)
