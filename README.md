# Pipeline de Analytics Engineering — Vendas E-commerce (Olist)

Pipeline de dados batch que processa o dataset público **Brazilian E-Commerce Public
Dataset by Olist** (Kaggle), valida qualidade, carrega em staging PostgreSQL e popula
um data mart dimensional (star schema) consumido via Power BI.

> Projeto construído seguindo a metodologia de **Spec-Driven Development (SDD)** e o
> guia de **Desenvolvimento Assistido por IA** do autor. Ver `docs/ai/` e
> `docs/specs/SPEC-001-pipeline-vendas.md`.

## Arquitetura

```text
CSV Olist (9 entidades)
        │
        ▼
Particionamento por data (simulação de batch diário)
        │
        ▼
Ingestão + Validação de schema
        │
        ▼
Qualidade de dados (quarentena de rejeitados)
        │
        ▼
Transformação (limpeza, tipagem, joins)
        │
        ▼
PostgreSQL — Staging
        │
        ▼
Modelagem dimensional — Star Schema
        │
        ▼
Power BI
```

## Status

✅ Pipeline completo, ponta a ponta: ingestão → qualidade → staging → data mart →
orquestração via Airflow. Todas as 9 entidades do dataset Olist implementadas, com
testes de integração reais (não mockados) contra PostgreSQL e, para as DAGs, contra
Airflow 2.9.3 de verdade.

**O que foi validado de verdade neste ambiente de desenvolvimento** (sem Docker
disponível): sintaxe/interpolação do `docker-compose.yml` via `docker compose config`
(binário standalone), lint dos dois `Dockerfile` via `hadolint` — ambos passaram sem
apontamentos. **O que NÃO foi validado:** build das imagens e subida real dos
containers, por falta do daemon Docker neste ambiente. Rode `./validate_docker.sh`
antes do primeiro `docker compose up` para conferir o que der para checar sem o
daemon, e trate o restante como não testado até você rodar de fato.

## Estrutura do repositório

```text
docs/
  specs/        # Especificações (SDD)
  architecture/ # Docs de arquitetura
  adr/          # Decisões arquiteturais
  security/     # Políticas de segurança
  conventions/  # Convenções de código
  runbooks/     # Procedimentos operacionais (inclui validação Docker)
  ai/           # Contexto para IA
src/            # Código fonte (ingestion, quality, loading, models)
dags/           # DAGs do Airflow (seed de referência + pipeline diário)
tests/          # unit, integration
infra/          # docker-compose auxiliar do Airflow, init-scripts
scripts/        # Scripts auxiliares (simulação de batch, execução do pipeline)
Dockerfile              # Imagem da aplicação (build context: raiz do repo)
docker-compose.yml      # Orquestração completa (Postgres + app + Airflow)
validate_docker.sh      # Validação estática do setup Docker (sem precisar do daemon)
```

## Setup local (sem Docker)

Útil para rodar testes/scripts rapidamente sem subir containers — requer um
PostgreSQL acessível localmente (ver `CONTRIBUTING.md` para detalhes):

```bash
cp .env.example .env   # preencha as variáveis
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit tests/integration
```

## Docker

### Serviços

| Serviço | Papel | Fica rodando? |
|---|---|---|
| `postgres` | Banco único, hospeda `staging`/`mart` do pipeline + `airflow_metastore` | Sim |
| `app` | Container da aplicação — pipeline, scripts, testes, shell ad-hoc | Sim (idle; comandos via `exec`) |
| `airflow-init` | Migra o metastore do Airflow, cria usuário admin | Não (roda e sai) |
| `airflow-webserver` | UI do Airflow (`localhost:8080`) | Sim |
| `airflow-scheduler` | Agenda/executa as DAGs | Sim |

### Setup

```bash
cp .env.example .env
# preencha POSTGRES_PASSWORD, AIRFLOW_ADMIN_PASSWORD e AIRFLOW_FERNET_KEY
# (gerar Fernet key: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

./validate_docker.sh   # checagem estática antes de subir qualquer coisa

docker build -t pipeline-vendas:latest .
docker compose up -d postgres app
```

### Rodando o pipeline via container `app`

O serviço `app` fica de pé (comando `tail -f /dev/null`) especificamente para
permitir `exec` — nenhum processo de aplicação roda sozinho dentro dele:

```bash
# Baixar/particionar dados (requer data/raw já populado com o dataset Kaggle)
docker compose exec app python -m scripts.simulate_daily_batches

# Rodar o pipeline completo para um dia (seed de referência + staging + mart)
docker compose exec app python -m scripts.run_pipeline --seed-reference --date 2017-05-10

# Rodar a suíte de testes dentro do container (mesmo ambiente do CI)
docker compose exec app pytest tests/unit tests/integration -q

# Shell interativo de depuração
docker compose exec app /bin/bash
```

Passo a passo completo de validação (com critérios de aceite):
`docs/runbooks/validacao_docker.md`.

### Subindo o Airflow (orquestração)

```bash
docker compose up airflow-init      # uma vez
docker compose up -d airflow-webserver airflow-scheduler
```

Acesse `http://localhost:8080` (usuário/senha definidos em `AIRFLOW_ADMIN_USER`/
`AIRFLOW_ADMIN_PASSWORD` no `.env`). Ordem de execução das DAGs:

1. `pipeline_vendas_seed_reference_dag` — manual, uma vez (carrega `products`/`sellers`).
2. `pipeline_vendas_daily_dag` — `@daily`, com `catchup=True` (processa cada dia simulado).

Ambas dependem de `python -m scripts.simulate_daily_batches` já ter populado
`data/landing/` (ver seção "Fonte de dados" abaixo).

### Encerrando

```bash
docker compose down            # mantém os volumes (dados do Postgres)
docker compose down --volumes  # remove tudo, incluindo o Postgres
```

## Fonte de dados

Dataset público Olist — baixar de:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
python -m scripts.simulate_daily_batches   # particiona em data/landing/
```

## De Analista a Engenheiro: onde os dois se encontram neste projeto

Este projeto foi desenhado para deixar visível a ponte entre as duas competências:

**Onde a Engenharia de Dados aparece:**
- Ingestão idempotente, validação de schema e quarentena de dados inválidos (`src/quality/`)
- Modelagem dimensional (star schema) — pensada não para "guardar dado", mas para que
  perguntas de negócio comuns (receita por categoria, por período, por vendedor) virem
  uma query simples, sem join complexo nem recálculo
- Orquestração via Airflow, containerização via Docker, testes de integração reais
  contra PostgreSQL (não mocks)

**Onde a Análise de Dados aparece:**
- `notebooks/analise_exploratoria.ipynb` — consome as `views` de BI já prontas
  (`src/loading/reporting_views.py`) para responder perguntas de negócio reais:
  quais categorias geram mais receita, como a demanda varia por dia da semana,
  se atraso de entrega correlaciona com nota de avaliação do cliente, distribuição
  geográfica de vendas

**Por que isso importa:** um Engenheiro de Dados que nunca fez análise tende a modelar dados
pensando em "como armazenar", não em "como alguém vai perguntar isso depois". A experiência
como Analista influenciou decisões de engenharia deste projeto — por exemplo, a agregação de
pagamentos por pedido em `dim_pagamento` (em vez de deixar o grão bruto de parcela) existe
porque, como analista, sei que ninguém quer fazer `GROUP BY` toda vez que precisa do valor
total pago por um pedido.

## Documentação

- Spec: `docs/specs/SPEC-001-pipeline-vendas.md`
- Contexto de IA: `docs/ai/project-context.md`
- Decisões arquiteturais: `docs/adr/`
- Runbook de validação Docker: `docs/runbooks/validacao_docker.md`
- Runbook de conexão Power BI: `docs/runbooks/conexao_powerbi.md`
- Contribuição: `CONTRIBUTING.md`
- Segurança: `SECURITY.md`

