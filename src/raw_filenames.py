"""Mapeamento entre nome lógico da entidade e nome real do arquivo no Kaggle.

Nomes confirmados contra o dataset real (ver docs/specs, seção "Contratos de
dados") — nunca inventados.
"""

from __future__ import annotations

RAW_FILENAMES: dict[str, str] = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Entidades transacionais: cada linha pertence a um pedido específico, então
# fazem sentido "chegar" em um dia específico (simulação de batch diário).
TRANSACTIONAL_ENTITIES: tuple[str, ...] = (
    "orders",
    "customers",
    "order_items",
    "order_payments",
    "order_reviews",
)

# Entidades de referência: catálogos que não pertencem a um pedido específico
# (um produto não "acontece" em uma data) — chegam como snapshot completo, não
# particionado por dia. Ver docstring de scripts/simulate_daily_batches.py.
REFERENCE_ENTITIES: tuple[str, ...] = (
    "products",
    "sellers",
    "geolocation",
    "category_translation",
)
