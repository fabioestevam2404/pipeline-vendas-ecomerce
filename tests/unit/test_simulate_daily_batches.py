from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.simulate_daily_batches import simulate_daily_batches
from src.config import Settings


def _escrever_csv(diretorio: Path, nome_arquivo: str, conteudo: str) -> None:
    (diretorio / nome_arquivo).write_text(conteudo)


@pytest.fixture
def raw_data_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    _escrever_csv(
        raw_dir,
        "olist_orders_dataset.csv",
        "order_id,customer_id,order_status,order_purchase_timestamp,"
        "order_approved_at,order_delivered_carrier_date,"
        "order_delivered_customer_date,order_estimated_delivery_date\n"
        "ord-1,cust-1,delivered,2017-05-10 10:00:00,2017-05-10 12:00:00,"
        "2017-05-11 09:00:00,2017-05-15 14:00:00,2017-05-20 00:00:00\n"
        "ord-2,cust-2,delivered,2017-05-11 08:00:00,2017-05-11 09:00:00,"
        "2017-05-12 09:00:00,2017-05-16 14:00:00,2017-05-21 00:00:00\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_customers_dataset.csv",
        "customer_id,customer_unique_id,customer_zip_code_prefix,"
        "customer_city,customer_state\n"
        "cust-1,uniq-1,14409,franca,SP\n"
        "cust-2,uniq-2,9790,sao bernardo do campo,SP\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_order_items_dataset.csv",
        "order_id,order_item_id,product_id,seller_id,shipping_limit_date,"
        "price,freight_value\n"
        "ord-1,1,prod-1,seller-1,2017-05-12 10:00:00,100.0,10.0\n"
        "ord-2,1,prod-2,seller-1,2017-05-13 10:00:00,50.0,5.0\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_order_payments_dataset.csv",
        "order_id,payment_sequential,payment_type,payment_installments,"
        "payment_value\n"
        "ord-1,1,credit_card,3,110.0\n"
        "ord-2,1,boleto,1,55.0\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_order_reviews_dataset.csv",
        "review_id,order_id,review_score,review_comment_title,"
        "review_comment_message,review_creation_date,review_answer_timestamp\n"
        "rev-1,ord-1,5,,,2017-05-16 10:00:00,2017-05-17 09:00:00\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_products_dataset.csv",
        "product_id,product_category_name,product_name_lenght,"
        "product_description_lenght,product_photos_qty,product_weight_g,"
        "product_length_cm,product_height_cm,product_width_cm\n"
        "prod-1,beleza_saude,40,500,2,500,20,10,15\n"
        "prod-2,informatica_acessorios,35,300,1,800,25,12,18\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_sellers_dataset.csv",
        "seller_id,seller_zip_code_prefix,seller_city,seller_state\n"
        "seller-1,13023,campinas,SP\n",
    )
    _escrever_csv(
        raw_dir,
        "olist_geolocation_dataset.csv",
        "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,"
        "geolocation_city,geolocation_state\n"
        "14409,-20.5,-47.4,franca,SP\n",
    )
    _escrever_csv(
        raw_dir,
        "product_category_name_translation.csv",
        "product_category_name,product_category_name_english\n"
        "beleza_saude,health_beauty\n",
    )
    return raw_dir


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


def test_particiona_orders_por_data_de_compra(
    raw_data_dir: Path, tmp_path: Path
) -> None:
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir, landing_zone_dir)

    simulate_daily_batches(settings)

    assert (landing_zone_dir / "orders" / "2017-05-10.csv").exists()
    assert (landing_zone_dir / "orders" / "2017-05-11.csv").exists()

    dia_10 = pd.read_csv(landing_zone_dir / "orders" / "2017-05-10.csv")
    assert list(dia_10["order_id"]) == ["ord-1"]


def test_entidades_sem_data_propria_sao_particionadas_via_order_id(
    raw_data_dir: Path, tmp_path: Path
) -> None:
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir, landing_zone_dir)

    simulate_daily_batches(settings)

    itens_dia_10 = pd.read_csv(landing_zone_dir / "order_items" / "2017-05-10.csv")
    assert list(itens_dia_10["order_id"]) == ["ord-1"]

    pagamentos_dia_11 = pd.read_csv(
        landing_zone_dir / "order_payments" / "2017-05-11.csv"
    )
    assert list(pagamentos_dia_11["order_id"]) == ["ord-2"]


def test_entidades_de_referencia_nao_sao_particionadas(
    raw_data_dir: Path, tmp_path: Path
) -> None:
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir, landing_zone_dir)

    simulate_daily_batches(settings)

    assert (landing_zone_dir / "reference" / "products.csv").exists()
    assert (landing_zone_dir / "reference" / "sellers.csv").exists()
    assert (landing_zone_dir / "reference" / "geolocation.csv").exists()
    assert (landing_zone_dir / "reference" / "category_translation.csv").exists()
    # Não deve existir uma pasta "products/" particionada por data.
    assert not (landing_zone_dir / "products").exists()


def test_dry_run_nao_escreve_nenhum_arquivo(raw_data_dir: Path, tmp_path: Path) -> None:
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir, landing_zone_dir)

    relatorio = simulate_daily_batches(settings, dry_run=True)

    assert not landing_zone_dir.exists()
    # O relatório ainda deve refletir o que SERIA escrito.
    assert relatorio["orders"][date(2017, 5, 10)] == 1
    assert relatorio["orders"][date(2017, 5, 11)] == 1


def test_filtro_de_data_afeta_arquivos_escritos_de_verdade(
    raw_data_dir: Path, tmp_path: Path
) -> None:
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir, landing_zone_dir)

    simulate_daily_batches(
        settings, start_date=date(2017, 5, 11), end_date=date(2017, 5, 11)
    )

    # Regressão: o filtro precisa valer para os arquivos escritos em disco,
    # não só para o relatório impresso (bug encontrado e corrigido nesta fatia).
    assert not (landing_zone_dir / "orders" / "2017-05-10.csv").exists()
    assert (landing_zone_dir / "orders" / "2017-05-11.csv").exists()
    assert not (landing_zone_dir / "order_reviews" / "2017-05-10.csv").exists()

    itens_dia_11 = pd.read_csv(landing_zone_dir / "order_items" / "2017-05-11.csv")
    assert list(itens_dia_11["order_id"]) == ["ord-2"]


def test_raise_ao_faltar_arquivo_bruto(tmp_path: Path) -> None:
    raw_data_dir_vazio = tmp_path / "raw_vazio"
    raw_data_dir_vazio.mkdir()
    landing_zone_dir = tmp_path / "landing"
    settings = _settings(raw_data_dir_vazio, landing_zone_dir)

    with pytest.raises(FileNotFoundError, match="olist_orders_dataset.csv"):
        simulate_daily_batches(settings)
