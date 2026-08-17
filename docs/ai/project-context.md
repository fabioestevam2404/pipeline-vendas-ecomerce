# Contexto do Projeto — Pipeline de Vendas E-commerce (Olist)

> Este documento é contexto governado para uso por desenvolvedores e agentes de IA.
> Ver `SPEC-001-pipeline-vendas.md` para requisitos completos.

## Visão geral

Pipeline batch (simulando ingestão diária) que processa os 9 arquivos CSV do dataset
público Olist (Brazilian E-commerce), valida qualidade de dados, carrega em staging
PostgreSQL e popula um data mart em modelo dimensional (star schema) consumido via Power BI.

**Natureza do dataset:** histórico e estático (pedidos 2016–2018). A "chegada diária" é
simulada por um script de particionamento (`scripts/simulate_daily_batches.py`) que
quebra o dataset por `order_purchase_timestamp`. Isso é uma decisão de design deliberada
para fins de portfólio/demonstração de arquitetura — não confundir com ingestão real.

## Arquitetura (visão resumida)

```text
CSV Olist (9 entidades)
        │
        ▼
scripts/simulate_daily_batches.py  (particiona por data → landing zone)
        │
        ▼
Airflow DAG (orquestra as etapas abaixo diariamente — ver ADR-001)
        │
        ▼
src/ingestion    → detecção de arquivo + validação de schema
        │
        ▼
src/quality      → regras de qualidade de dados, quarentena de rejeitados
        │
        ▼
src/transformation → limpeza, tipagem, deduplicação, joins
        │
        ▼
PostgreSQL — staging (via Docker Compose)
        │
        ▼
src/loading      → modelagem dimensional (star schema)
        │
        ▼
PostgreSQL — data mart
        │
        ▼
Power BI
```

## Limites de componentes e responsabilidades

| Componente | Responsabilidade | Não deve fazer |
|---|---|---|
| `src/ingestion` | Detectar arquivos, validar schema básico | Transformação de negócio |
| `src/quality` | Validar regras de qualidade, rotear rejeitados | Corrigir dados silenciosamente |
| `src/quality/common.py` | Helpers compartilhados entre entidades (normalização de nulos, duplicatas) | Regra de negócio específica de uma entidade |
| `src/transformation` | Limpeza, tipagem, joins, deduplicação | Lógica de carga no DW |
| `src/loading` | Popular staging e data mart, transformações dimensionais (ex.: `dim_customers`) | Validação de qualidade |
| `src/models` | Definições de schema/dataclasses das entidades | Lógica de I/O |

## Entidades implementadas até o momento

| Entidade | Ingestão/Schema | Qualidade | Observações |
|---|---|---|---|
| `orders` | ✅ | ✅ | Core do modelo; regras de data (futuro, entrega antes da compra) |
| `customers` | — (usa schema genérico) | ✅ | UF validada contra lista de siglas BR |
| `order_items` | — (usa schema genérico) | ✅ | Chave composta (order_id, order_item_id); checagem de chave órfã opcional |
| `products` | — (usa schema genérico) | ✅ | Colunas com grafia real do Kaggle (`product_name_lenght`); medidas negativas rejeitadas, categoria nula é válida |
| `sellers` | — (usa schema genérico) | ✅ | Mesmo padrão de `customers` (validação de UF), sem `unique_id` |
| `order_payments` | — (usa schema genérico) | ✅ | Chave composta (order_id, payment_sequential); `payment_type` validado contra os 5 valores reais (incl. `not_defined`) |
| `order_reviews` | — (usa schema genérico) | ✅ | `review_id` único (PK); `order_id` duplicado é PERMITIDO (dataset real tem pedidos com múltiplos reviews) |
| `dim_customers` (loading) | ✅ (transform) | — | Enriquecida com geolocalização (lat/lng médios, cidade/estado mais frequente por CEP); inclui `customer_sk` |
| `dim_products` (loading) | ✅ (transform) | — | Tradução de categoria PT→EN; produto sem categoria não é descartado |
| `dim_sellers` (loading) | ✅ (transform) | — | Mesmo enriquecimento por geolocalização de `dim_customers`, via helper compartilhado (`src/loading/geolocation.py`) |
| `dim_tempo` (loading) | ✅ (transform) | — | Gerada a partir das datas distintas de `order_purchase_timestamp`; `date_sk` no formato AAAAMMDD |
| `dim_pagamento` (loading) | ✅ (transform) | — | Agregada por PEDIDO (não por linha de pagamento) para evitar fan-out no fato; ver `src/loading/dim_pagamento.py` |
| `fato_pedidos` (loading) | ✅ (transform) | — | Granularidade: item de pedido. Resolve as 5 chaves substitutas completas: `customer_sk`, `produto_sk`, `vendedor_sk`, `date_sk`, `pagamento_sk`; `review_score` opcional (nulo quando o pedido não tem review) |
| `load_staging` (PostgreSQL) | ✅ | ✅ (integração real) | UPSERT idempotente para as 7 entidades transacionais + `products`/`sellers`, via `src/loading/load_staging.py` |
| `load_mart` (PostgreSQL) | ✅ | ✅ (integração real) | Schema `mart`: `dim_customers`, `dim_tempo`, `dim_products`, `dim_sellers`, `dim_pagamento` (todas com sk via IDENTITY, estável entre execuções), `fact_pedidos` (FK para as 5 dimensões) |
| Contrato original da spec (`fato_pedidos` completo) | ✅ | ✅ | Todas as colunas do contrato original (`docs/specs`, seção "Contratos de dados") estão implementadas: `cliente_sk`, `produto_sk`, `vendedor_sk`, `tempo_sk` (=date_sk), `pagamento_sk`, `review_score` |
| `scripts/simulate_daily_batches.py` | ✅ | ✅ (6 testes) | Particiona o dataset bruto simulando chegadas diárias (ADR-002); entidades de referência não são particionadas |
| `scripts/run_pipeline.py` | ✅ | ✅ (integração real) | Entrypoint executável do pipeline completo (seed + staging + mart para um dia), sem depender do Airflow — usado no runbook Docker |
| Orquestração via Airflow (`dags/`) | ✅ | ✅ (validado sob Airflow 2.9.3 real, não só sintaxe) | `pipeline_vendas_seed_reference_dag` (manual, uma vez) + `pipeline_vendas_daily_dag` (`@daily`, por `ds`). Ver ADR-001 (Airflow) |
| `docker-compose.yml`/`Dockerfile` (raiz do repo) | ✅ | ⚠️ não validado com `docker`/`docker compose` de verdade (daemon indisponível no ambiente de desenvolvimento) — sintaxe e lint (`hadolint`) validados de verdade | Postgres + `app` + Airflow completo. Runbook: `docs/runbooks/validacao_docker.md` |
| Views de consumo para BI (`src/loading/reporting_views.py`) | ✅ | ✅ (integração real) | `vw_vendas_por_produto`, `vw_vendas_por_vendedor`, `vw_vendas_por_periodo`, `vw_resumo_pedidos` — validadas batendo contra a origem. Guia de conexão: `docs/runbooks/conexao_powerbi.md` (conexão real com Power BI Desktop não testada — ferramenta indisponível no ambiente) |
| Alertas de falha (RNF "Observabilidade") | ❌ | — | Gap real, não hipotético: hoje só há `logger.error`/`logger.warning`, sem mecanismo de alerta (e-mail, Slack, PagerDuty). Registrado como pendência no critério de aceitação correspondente da spec |

## Stack e versões homologadas

- Python 3.11+
- Pandas (transformação)
- psycopg2 / SQLAlchemy (acesso PostgreSQL)
- PostgreSQL 16 (via Docker Compose)
- Apache Airflow (LocalExecutor, via Docker Compose — ver ADR-001) para orquestração
- pytest (testes)
- Docker / Docker Compose

**Bibliotecas proibidas/a evitar:** qualquer engine distribuída (Spark, Dask) — volume
(~100k pedidos) não justifica a complexidade nesta fase. Se o volume crescer
significativamente, essa decisão deve ser revisitada via ADR.

## Convenções de código

Ver `docs/ai/coding-rules.md`.

## Regras de segurança

Ver `docs/ai/security-rules.md`.

## Regras de teste

Ver `docs/ai/testing-rules.md`.

## Anti-padrões conhecidos (deste projeto)

- Não tratar o dataset simulado como se fosse ingestão real de produção — a documentação
  e os nomes de variáveis/logs devem deixar claro que é uma simulação de batch diário.
- Não silenciar erros de validação de schema — todo registro rejeitado precisa de motivo
  registrado (ver RF04 da spec).
- Não fazer carga direta no data mart sem passar por staging.
