"""Definição das tabelas do data mart (schema `mart`) via SQLAlchemy Core.

Diferença crítica em relação a `staging_schema.py`: `dim_customers.customer_sk`
é gerada pelo BANCO (`Identity`), não em memória — precisa ser estável entre
execuções do pipeline, já que `fact_pedidos` referencia essa chave por FK.
Se a sk fosse recalculada a cada rodada (como faz o `build_dim_customers`
puramente em memória, usado só para testes/transformação isolada), o mesmo
cliente ganharia uma sk diferente a cada execução e corromperia silenciosamente
a integridade do fato já carregado — daí a `dim_customers.customer_sk` viver
só no banco a partir desta fatia.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Identity,
    Integer,
    MetaData,
    String,
    Table,
    func,
)

MART_SCHEMA = "mart"

metadata = MetaData(schema=MART_SCHEMA)

dim_customers = Table(
    "dim_customers",
    metadata,
    Column("customer_sk", Integer, Identity(start=1), primary_key=True),
    Column("customer_id", String, nullable=False, unique=True),
    Column("customer_unique_id", String, nullable=False),
    Column("customer_zip_code_prefix", String, nullable=False),
    Column("customer_city", String, nullable=False),
    Column("customer_state", String, nullable=False),
    Column("geolocation_lat", Float, nullable=True),
    Column("geolocation_lng", Float, nullable=True),
    Column("geolocation_city", String, nullable=True),
    Column("geolocation_state", String, nullable=True),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

dim_tempo = Table(
    "dim_tempo",
    metadata,
    Column("date_sk", Integer, primary_key=True),  # AAAAMMDD, já determinístico
    Column("date", Date, nullable=False),
    Column("ano", Integer, nullable=False),
    Column("mes", Integer, nullable=False),
    Column("trimestre", Integer, nullable=False),
    Column("dia", Integer, nullable=False),
    Column("dia_da_semana", String, nullable=False),
    Column("fim_de_semana", Boolean, nullable=False),
)

dim_products = Table(
    "dim_products",
    metadata,
    Column("product_sk", Integer, Identity(start=1), primary_key=True),
    Column("product_id", String, nullable=False, unique=True),
    Column("product_category_name", String, nullable=True),
    Column("product_category_name_english", String, nullable=True),
    Column("product_name_lenght", Integer, nullable=True),
    Column("product_description_lenght", Integer, nullable=True),
    Column("product_photos_qty", Integer, nullable=True),
    Column("product_weight_g", Float, nullable=True),
    Column("product_length_cm", Float, nullable=True),
    Column("product_height_cm", Float, nullable=True),
    Column("product_width_cm", Float, nullable=True),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

dim_sellers = Table(
    "dim_sellers",
    metadata,
    Column("seller_sk", Integer, Identity(start=1), primary_key=True),
    Column("seller_id", String, nullable=False, unique=True),
    Column("seller_zip_code_prefix", String, nullable=False),
    Column("seller_city", String, nullable=False),
    Column("seller_state", String, nullable=False),
    Column("geolocation_lat", Float, nullable=True),
    Column("geolocation_lng", Float, nullable=True),
    Column("geolocation_city", String, nullable=True),
    Column("geolocation_state", String, nullable=True),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

dim_pagamento = Table(
    "dim_pagamento",
    metadata,
    Column("pagamento_sk", Integer, Identity(start=1), primary_key=True),
    Column("order_id", String, nullable=False, unique=True),
    Column("valor_total_pago", Float, nullable=False),
    Column("forma_pagamento_principal", String, nullable=False),
    Column("qtd_parcelas", Integer, nullable=False),
    Column("qtd_metodos_pagamento", Integer, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
)

fact_pedidos = Table(
    "fact_pedidos",
    metadata,
    Column("order_id", String, primary_key=True),
    Column("order_item_id", Integer, primary_key=True),
    Column("customer_sk", Integer, nullable=False),
    Column("produto_sk", Integer, nullable=False),
    Column("vendedor_sk", Integer, nullable=False),
    Column("date_sk", Integer, nullable=False),
    Column("pagamento_sk", Integer, nullable=False),
    Column("valor_item", Float, nullable=False),
    Column("valor_frete", Float, nullable=False),
    Column("review_score", Integer, nullable=True),  # nem todo pedido tem review
    Column("batch_date", Date, nullable=False),
    Column("loaded_at", DateTime, nullable=False, server_default=func.now()),
    ForeignKeyConstraint(["customer_sk"], ["mart.dim_customers.customer_sk"]),
    ForeignKeyConstraint(["date_sk"], ["mart.dim_tempo.date_sk"]),
    ForeignKeyConstraint(["produto_sk"], ["mart.dim_products.product_sk"]),
    ForeignKeyConstraint(["vendedor_sk"], ["mart.dim_sellers.seller_sk"]),
    ForeignKeyConstraint(["pagamento_sk"], ["mart.dim_pagamento.pagamento_sk"]),
)
