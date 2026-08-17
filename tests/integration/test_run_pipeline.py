from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import Engine, text

from scripts.run_pipeline import process_day, seed_reference_data
from src.config import Settings


def _settings(raw_data_dir: Path, landing_zone_dir: Path) -> Settings:
    return Settings(
        postgres_user="x",
        postgres_password="x",
        postgres_db="x",
        postgres_host="localhost",
        postgres_port=5432,
        raw_data_dir=raw_data_dir,
        landing_zone_dir=landing_zone_dir,
        quarantine_dir=landing_zone_dir / "quarantine",
    )


def _popular_landing_zone(landing_zone_dir: Path) -> None:
    """Popula uma landing zone mínima, no formato que
    `scripts.simulate_daily_batches` produziria."""
    (landing_zone_dir / "orders").mkdir(parents=True)
    (landing_zone_dir / "orders" / "2017-05-10.csv").write_text(
        "order_id,customer_id,order_status,order_purchase_timestamp,"
        "order_approved_at,order_delivered_carrier_date,"
        "order_delivered_customer_date,order_estimated_delivery_date\n"
        "ord-1,cust-1,delivered,2017-05-10 10:00:00,2017-05-10 12:00:00,"
        "2017-05-11 09:00:00,2017-05-15 14:00:00,2017-05-20 00:00:00\n"
    )

    (landing_zone_dir / "customers").mkdir(parents=True)
    (landing_zone_dir / "customers" / "2017-05-10.csv").write_text(
        "customer_id,customer_unique_id,customer_zip_code_prefix,"
        "customer_city,customer_state\n"
        "cust-1,uniq-1,14409,franca,SP\n"
    )

    (landing_zone_dir / "order_items").mkdir(parents=True)
    (landing_zone_dir / "order_items" / "2017-05-10.csv").write_text(
        "order_id,order_item_id,product_id,seller_id,shipping_limit_date,"
        "price,freight_value\n"
        "ord-1,1,prod-1,seller-1,2017-05-12 10:00:00,100.0,10.0\n"
    )

    (landing_zone_dir / "order_payments").mkdir(parents=True)
    (landing_zone_dir / "order_payments" / "2017-05-10.csv").write_text(
        "order_id,payment_sequential,payment_type,payment_installments,"
        "payment_value\n"
        "ord-1,1,credit_card,3,110.0\n"
    )

    (landing_zone_dir / "order_reviews").mkdir(parents=True)
    (landing_zone_dir / "order_reviews" / "2017-05-10.csv").write_text(
        "review_id,order_id,review_score,review_comment_title,"
        "review_comment_message,review_creation_date,review_answer_timestamp\n"
        "rev-1,ord-1,5,,,2017-05-16 10:00:00,2017-05-17 09:00:00\n"
    )

    (landing_zone_dir / "reference").mkdir(parents=True)
    (landing_zone_dir / "reference" / "products.csv").write_text(
        "product_id,product_category_name,product_name_lenght,"
        "product_description_lenght,product_photos_qty,product_weight_g,"
        "product_length_cm,product_height_cm,product_width_cm\n"
        "prod-1,beleza_saude,40,500,2,500,20,10,15\n"
    )
    (landing_zone_dir / "reference" / "sellers.csv").write_text(
        "seller_id,seller_zip_code_prefix,seller_city,seller_state\n"
        "seller-1,13023,campinas,SP\n"
    )
    (landing_zone_dir / "reference" / "geolocation.csv").write_text(
        "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,"
        "geolocation_city,geolocation_state\n"
        "14409,-20.5,-47.4,franca,SP\n"
    )
    (landing_zone_dir / "reference" / "category_translation.csv").write_text(
        "product_category_name,product_category_name_english\n"
        "beleza_saude,health_beauty\n"
    )


def test_run_pipeline_ponta_a_ponta_popula_fact_pedidos(
    engine: Engine, tmp_path: Path
) -> None:
    """Reaproveita a fixture `engine` (schema staging já criado) de
    tests/integration/conftest.py, mas aqui o alvo é o resultado no schema
    `mart`, que este teste cria via `create_mart_schema` dentro do próprio
    fluxo de `seed_reference_data`/`process_day` (chamadas no script real
    passam por `main()`, que cria os schemas — aqui chamamos as funções
    diretamente, então garantimos a criação do schema mart manualmente)."""
    from src.loading.load_mart import create_mart_schema

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS mart CASCADE"))
    create_mart_schema(engine)

    landing_zone_dir = tmp_path / "landing"
    _popular_landing_zone(landing_zone_dir)
    settings = _settings(tmp_path / "raw", landing_zone_dir)

    # Monkeypatch simples: as funções do script chamam get_engine(settings),
    # que exige as env vars do processo — usamos a fixture `engine` (já
    # aponta pro Postgres de teste) diretamente nas funções em vez de recriar
    # a engine a partir de settings fake.
    import scripts.run_pipeline as run_pipeline_module

    original_get_engine = run_pipeline_module.get_engine
    run_pipeline_module.get_engine = lambda _settings: engine
    try:
        seed_reference_data(settings)
        process_day(settings, date(2017, 5, 10))
    finally:
        run_pipeline_module.get_engine = original_get_engine

    with engine.connect() as conn:
        resultado = conn.execute(text("""
                SELECT f.order_id, f.review_score, c.customer_id, p.product_id
                FROM mart.fact_pedidos f
                JOIN mart.dim_customers c ON c.customer_sk = f.customer_sk
                JOIN mart.dim_products p ON p.product_sk = f.produto_sk
                """)).fetchall()

    assert len(resultado) == 1
    assert resultado[0].order_id == "ord-1"
    assert resultado[0].review_score == 5
    assert resultado[0].customer_id == "cust-1"
    assert resultado[0].product_id == "prod-1"

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS mart CASCADE"))
