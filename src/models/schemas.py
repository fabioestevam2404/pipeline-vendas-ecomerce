"""Schemas das entidades do dataset Olist.

Nesta fatia da implementação, apenas a entidade `orders` (core do modelo) está
definida. As demais entidades (customers, order_items, order_payments,
order_reviews, products, sellers, geolocation, product_category_name_translation)
entram em fatias seguintes, conforme docs/specs/SPEC-001-pipeline-vendas.md.

Colunas confirmadas contra o dataset real (ver docs/specs, seção Contratos de dados).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

# Valores válidos observados para order_status no dataset Olist (8 valores únicos).
VALID_ORDER_STATUSES = frozenset(
    {
        "created",
        "approved",
        "invoiced",
        "processing",
        "shipped",
        "delivered",
        "unavailable",
        "canceled",
    }
)

# Nome exato das colunas esperadas no arquivo olist_orders_dataset.csv,
# na ordem em que aparecem na fonte original.
ORDERS_EXPECTED_COLUMNS: list[str] = [
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


class OrderRecord(BaseModel):
    """Representa uma linha válida de `olist_orders_dataset.csv`.

    Campos de data que podem ser nulos na fonte real (ex.: pedido ainda não
    aprovado) são Optional — a ausência desses campos não é, por si só, motivo
    de rejeição (ver docs/specs, Requisitos Funcionais RF03).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: str
    customer_id: str
    order_status: str
    order_purchase_timestamp: datetime
    order_approved_at: datetime | None = None
    order_delivered_carrier_date: datetime | None = None
    order_delivered_customer_date: datetime | None = None
    order_estimated_delivery_date: datetime

    @field_validator("order_status")
    @classmethod
    def validar_status_conhecido(cls, valor: str) -> str:
        if valor not in VALID_ORDER_STATUSES:
            raise ValueError(
                f"order_status '{valor}' fora do conjunto de valores conhecidos: "
                f"{sorted(VALID_ORDER_STATUSES)}"
            )
        return valor

    @field_validator("order_id", "customer_id")
    @classmethod
    def validar_id_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("identificador não pode ser vazio")
        return valor


# --- Customers -------------------------------------------------------------
# Colunas confirmadas: olist_customers_dataset.csv (5 colunas, 99441 linhas).
CUSTOMERS_EXPECTED_COLUMNS: list[str] = [
    "customer_id",
    "customer_unique_id",
    "customer_zip_code_prefix",
    "customer_city",
    "customer_state",
]

# Siglas de estado brasileiras válidas — usadas para detectar dado corrompido
# (ex.: coluna deslocada por vírgula mal escapada em algum campo de texto).
VALID_BR_STATE_CODES = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)


class CustomerRecord(BaseModel):
    """Representa uma linha válida de `olist_customers_dataset.csv`.

    `customer_id` é o identificador ligado a `orders.customer_id` — um pedido
    tem um `customer_id` diferente a cada compra. `customer_unique_id` é o
    identificador estável da pessoa entre pedidos (ver spec, contratos de
    dados). Ambos são tratados como pseudonimizados (docs/ai/security-rules.md).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str
    customer_unique_id: str
    customer_zip_code_prefix: str
    customer_city: str
    customer_state: str

    @field_validator("customer_id", "customer_unique_id", "customer_zip_code_prefix")
    @classmethod
    def validar_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return valor

    @field_validator("customer_state")
    @classmethod
    def validar_uf(cls, valor: str) -> str:
        valor_upper = valor.upper()
        if valor_upper not in VALID_BR_STATE_CODES:
            raise ValueError(f"customer_state '{valor}' não é uma UF brasileira válida")
        return valor_upper


# --- Order items -------------------------------------------------------------
# Colunas confirmadas: olist_order_items_dataset.csv (7 colunas). Granularidade:
# uma linha por item de pedido; chave composta (order_id, order_item_id).
ORDER_ITEMS_EXPECTED_COLUMNS: list[str] = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "shipping_limit_date",
    "price",
    "freight_value",
]


class OrderItemRecord(BaseModel):
    """Representa uma linha válida de `olist_order_items_dataset.csv`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    shipping_limit_date: datetime
    price: float
    freight_value: float

    @field_validator("order_id", "product_id", "seller_id")
    @classmethod
    def validar_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return valor

    @field_validator("order_item_id")
    @classmethod
    def validar_item_id_positivo(cls, valor: int) -> int:
        if valor < 1:
            raise ValueError("order_item_id deve ser >= 1")
        return valor

    @field_validator("price", "freight_value")
    @classmethod
    def validar_valor_nao_negativo(cls, valor: float) -> float:
        if valor < 0:
            raise ValueError("valor monetário não pode ser negativo")
        return valor


# --- Geolocation ---------------------------------------------------------
# Usado apenas para enriquecimento de dim_customers (src/loading), não passa
# pelo mesmo fluxo de qualidade/quarentena das entidades transacionais — é
# dado de referência estático (CEP -> lat/lng/cidade/estado).
GEOLOCATION_EXPECTED_COLUMNS: list[str] = [
    "geolocation_zip_code_prefix",
    "geolocation_lat",
    "geolocation_lng",
    "geolocation_city",
    "geolocation_state",
]


# --- Products --------------------------------------------------------------
# Colunas confirmadas: olist_products_dataset.csv (9 colunas, 32951 linhas).
# ATENÇÃO: `product_name_lenght` e `product_description_lenght` têm esse nome
# EXATO no arquivo real do Kaggle (sem o "g" antes de "th" — erro de digitação
# de origem, não nosso). Mantido de propósito para bater com o dado real; ver
# docs/ai/coding-rules.md ("não inventar colunas").
PRODUCTS_EXPECTED_COLUMNS: list[str] = [
    "product_id",
    "product_category_name",
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

CATEGORY_TRANSLATION_EXPECTED_COLUMNS: list[str] = [
    "product_category_name",
    "product_category_name_english",
]


class ProductRecord(BaseModel):
    """Representa uma linha válida de `olist_products_dataset.csv`.

    Vários campos são opcionais porque o dataset real tem nulos legítimos
    (ex.: ~610 produtos sem `product_category_name`, alguns sem dimensões) —
    ver docs/specs, "Casos de erro e borda". Um produto sem categoria não é,
    por si só, um erro de qualidade; produto com peso/dimensão NEGATIVA é.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: str
    product_category_name: str | None = None
    product_name_lenght: int | None = None
    product_description_lenght: int | None = None
    product_photos_qty: int | None = None
    product_weight_g: float | None = None
    product_length_cm: float | None = None
    product_height_cm: float | None = None
    product_width_cm: float | None = None

    @field_validator("product_id")
    @classmethod
    def validar_id_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("product_id não pode ser vazio")
        return valor

    @field_validator(
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"
    )
    @classmethod
    def validar_medida_nao_negativa(cls, valor: float | None) -> float | None:
        if valor is not None and valor < 0:
            raise ValueError("medida física não pode ser negativa")
        return valor


# --- Sellers -----------------------------------------------------------------
# Colunas confirmadas: olist_sellers_dataset.csv (4 colunas) — mesmo padrão de
# `customers`, sem `unique_id` (um seller_id já identifica o vendedor).
SELLERS_EXPECTED_COLUMNS: list[str] = [
    "seller_id",
    "seller_zip_code_prefix",
    "seller_city",
    "seller_state",
]


class SellerRecord(BaseModel):
    """Representa uma linha válida de `olist_sellers_dataset.csv`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    seller_id: str
    seller_zip_code_prefix: str
    seller_city: str
    seller_state: str

    @field_validator("seller_id", "seller_zip_code_prefix")
    @classmethod
    def validar_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return valor

    @field_validator("seller_state")
    @classmethod
    def validar_uf(cls, valor: str) -> str:
        valor_upper = valor.upper()
        if valor_upper not in VALID_BR_STATE_CODES:
            raise ValueError(f"seller_state '{valor}' não é uma UF brasileira válida")
        return valor_upper


# --- Order payments ----------------------------------------------------------
# Colunas confirmadas: olist_order_payments_dataset.csv (5 colunas). Um pedido
# pode ter múltiplas linhas de pagamento (pagamento dividido em métodos ou
# parcelas registradas separadamente) — chave composta (order_id, payment_sequential).
ORDER_PAYMENTS_EXPECTED_COLUMNS: list[str] = [
    "order_id",
    "payment_sequential",
    "payment_type",
    "payment_installments",
    "payment_value",
]

# Valores reais observados em payment_type, incluindo 'not_defined', que
# aparece num pequeno número de linhas do dataset real (não é erro nosso).
VALID_PAYMENT_TYPES = frozenset(
    {"credit_card", "boleto", "voucher", "debit_card", "not_defined"}
)


class PaymentRecord(BaseModel):
    """Representa uma linha válida de `olist_order_payments_dataset.csv`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: str
    payment_sequential: int
    payment_type: str
    payment_installments: int
    payment_value: float

    @field_validator("order_id")
    @classmethod
    def validar_order_id_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("order_id não pode ser vazio")
        return valor

    @field_validator("payment_type")
    @classmethod
    def validar_tipo_conhecido(cls, valor: str) -> str:
        if valor not in VALID_PAYMENT_TYPES:
            raise ValueError(
                f"payment_type '{valor}' fora do conjunto conhecido: "
                f"{sorted(VALID_PAYMENT_TYPES)}"
            )
        return valor

    @field_validator("payment_sequential")
    @classmethod
    def validar_sequencial_positivo(cls, valor: int) -> int:
        if valor < 1:
            raise ValueError("payment_sequential deve ser >= 1")
        return valor

    @field_validator("payment_installments")
    @classmethod
    def validar_parcelas_nao_negativas(cls, valor: int) -> int:
        if valor < 0:
            raise ValueError("payment_installments não pode ser negativo")
        return valor

    @field_validator("payment_value")
    @classmethod
    def validar_valor_nao_negativo(cls, valor: float) -> float:
        if valor < 0:
            raise ValueError("payment_value não pode ser negativo")
        return valor


# --- Order reviews -------------------------------------------------------------
# Colunas confirmadas: olist_order_reviews_dataset.csv (7 colunas). ATENÇÃO:
# o dataset real tem order_id com MÚLTIPLOS reviews em alguns casos, e há uma
# anomalia documentada de review_id duplicado apontando para order_ids
# diferentes com timestamp idêntico — tratado na camada de loading
# (dim_pagamento/fato), não aqui: aqui só validamos a linha em si.
ORDER_REVIEWS_EXPECTED_COLUMNS: list[str] = [
    "review_id",
    "order_id",
    "review_score",
    "review_comment_title",
    "review_comment_message",
    "review_creation_date",
    "review_answer_timestamp",
]


class ReviewRecord(BaseModel):
    """Representa uma linha válida de `olist_order_reviews_dataset.csv`.

    `review_comment_title`/`review_comment_message` são frequentemente nulos
    no dataset real (a maioria dos clientes não escreve comentário, só dá a
    nota) — nulo aqui não é erro de qualidade.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    review_id: str
    order_id: str
    review_score: int
    review_comment_title: str | None = None
    review_comment_message: str | None = None
    review_creation_date: datetime
    review_answer_timestamp: datetime | None = None

    @field_validator("review_id", "order_id")
    @classmethod
    def validar_id_nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("identificador não pode ser vazio")
        return valor

    @field_validator("review_score")
    @classmethod
    def validar_nota_entre_1_e_5(cls, valor: int) -> int:
        if not 1 <= valor <= 5:
            raise ValueError("review_score deve estar entre 1 e 5")
        return valor
