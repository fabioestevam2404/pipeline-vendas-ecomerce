# Runbook — Validação da Stack Docker

> Este runbook assume o daemon Docker disponível. Neste repositório, ele foi
> escrito e revisado, mas **não executado de ponta a ponta** — o ambiente de
> desenvolvimento usado para construir o projeto não tinha Docker disponível
> (ver `AI_USAGE.md`, seção "Limitações conhecidas"). O que foi validado sem
> o daemon: sintaxe/interpolação do `docker-compose.yml` (`docker compose
> config`) e lint dos `Dockerfile` (`hadolint`), ambos com resultado limpo.
> A lógica de `scripts/run_pipeline.py` (chamada no passo 5) foi validada de
> verdade contra PostgreSQL real, fora do container — ver
> `tests/integration/test_run_pipeline.py`.

## Pré-requisitos

- Docker e Docker Compose instalados.
- `.env` criado a partir de `.env.example`, com `POSTGRES_PASSWORD`,
  `AIRFLOW_ADMIN_PASSWORD` e `AIRFLOW_FERNET_KEY` preenchidos.
- Dataset Olist baixado em `data/raw/` e particionado em `data/landing/`
  (ver README.md, seção "Fonte de dados") — os passos 5 e 6 abaixo não têm
  o que processar sem isso.

Rode `./validate_docker.sh` antes de começar — ele cobre a checagem estática
(sintaxe, lint) sem precisar do daemon.

## Sequência de validação

```bash
# 1. Validar build da imagem da aplicação
docker build -t pipeline-vendas:latest .

# 2. Subir a stack completa (Postgres + app + Airflow)
docker compose up -d

# 2b. Inicializar o metastore do Airflow (uma vez, antes do primeiro uso)
docker compose up airflow-init

# 3. Verificar saúde dos containers
docker compose ps

# 4. Testar conexão PostgreSQL a partir do container app
#    (usa as variáveis reais do projeto — ver .env.example — não "postgres"/
#    "pipeline_vendas" genéricos, que não existem neste setup)
docker compose exec app python -c "
from src.config import load_settings
from src.db import get_engine
from sqlalchemy import text
engine = get_engine(load_settings())
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"

# 4b. Alternativa via psql direto no container postgres
docker compose exec postgres psql -U "${POSTGRES_USER:-pipeline_user}" \
  -d "${POSTGRES_DB:-vendas_ecommerce}" -c "SELECT 1;"

# 5. Executar o pipeline (seed de referência + um dia simulado)
#    Substitui `python src/loading/load_mart.py` do rascunho original —
#    aquele arquivo é um módulo de biblioteca, não tem entrypoint executável.
docker compose exec app python -m scripts.run_pipeline \
  --seed-reference --date 2017-05-10

# 6. Verificar dados carregados no schema mart
docker compose exec postgres psql -U "${POSTGRES_USER:-pipeline_user}" \
  -d "${POSTGRES_DB:-vendas_ecommerce}" -c \
  "SELECT COUNT(*) FROM mart.fact_pedidos;"

# 6b. Verificação mais completa: conferir que as chaves substitutas resolveram
docker compose exec postgres psql -U "${POSTGRES_USER:-pipeline_user}" \
  -d "${POSTGRES_DB:-vendas_ecommerce}" -c \
  "SELECT f.order_id, c.customer_id, p.product_id, s.seller_id, f.review_score
   FROM mart.fact_pedidos f
   JOIN mart.dim_customers c ON c.customer_sk = f.customer_sk
   JOIN mart.dim_products  p ON p.product_sk  = f.produto_sk
   JOIN mart.dim_sellers   s ON s.seller_sk   = f.vendedor_sk
   ORDER BY f.order_id;"

# 7. Rodar a suíte de testes dentro do container (mesmo ambiente do CI)
docker compose exec app pytest tests/unit tests/integration -q

# 8. Conferir logs em busca de erros/warnings críticos
docker compose logs app --tail=200
docker compose logs airflow-scheduler --tail=200 | grep -iE "error|critical" || echo "sem erros críticos"
```

## Critérios de aceite

- [ ] `docker build -t pipeline-vendas:latest .` completa sem erros.
- [ ] `docker compose up -d` sobe `postgres`, `app`, `airflow-webserver`,
      `airflow-scheduler` (após `airflow-init` ter rodado uma vez).
- [ ] `docker compose ps` mostra todos os serviços com status saudável
      (`healthy` para `postgres` e `airflow-webserver`, que têm healthcheck).
- [ ] Conexão PostgreSQL funciona a partir do container `app` (passo 4).
- [ ] `python -m scripts.run_pipeline --seed-reference --date 2017-05-10`
      executa sem erros e loga `fact_pedidos_do_dia_concluido`.
- [ ] `SELECT COUNT(*) FROM mart.fact_pedidos` retorna um valor > 0.
- [ ] A query do passo 6b retorna linhas com `customer_id`, `product_id`,
      `seller_id` preenchidos (confirma que as sk resolveram de verdade,
      não só que a tabela tem linhas).
- [ ] `pytest tests/unit tests/integration -q` (passo 7) passa 100% dentro
      do container — mesmo resultado que roda no CI (`.github/workflows/ci.yml`).
- [ ] Logs (`docker compose logs`) não mostram erro/critical não esperado —
      `WARNING` de "sem geolocalização" ou "sem review" são esperados e
      documentados (ver `docs/ai/project-context.md`), não são falha.

## Encerrando

```bash
docker compose down            # mantém os volumes (dados do Postgres)
docker compose down --volumes  # remove tudo, incluindo o Postgres
```

## Se algo falhar

- **Passo 1 falha:** confira `.dockerignore` não está excluindo `src/`,
  `scripts/`, `dags/`, ou `requirements*.txt` por engano.
- **Passo 2 falha (`postgres` não sobe saudável):** confira
  `infra/init-scripts/001_create_airflow_metastore.sql` — só roda em volume
  vazio; se já existe um volume `postgres_data` antigo, rode
  `docker compose down --volumes` antes de tentar de novo.
- **Passo 5 falha com "Arquivo bruto não encontrado":** rode
  `python -m scripts.simulate_daily_batches` (fora do container, ou via
  `docker compose exec app python -m scripts.simulate_daily_batches`) antes
  — o pipeline não baixa nem particiona o dataset sozinho.
- **Passo 6 retorna 0:** confira se o passo 5 rodou com `--seed-reference`
  incluído — sem `dim_products`/`dim_sellers` populadas, os itens do fato são
  descartados silenciosamente (comportamento intencional, documentado em
  `src/loading/fact_pedidos.py` — não é bug).
