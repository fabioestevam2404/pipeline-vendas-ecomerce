# Uso de IA neste Projeto

Este projeto foi planejado seguindo a metodologia Spec-Driven Development (SDD) e o
guia de Desenvolvimento Assistido por IA do autor (`docs/ai/`).

## Fases concluídas com apoio de IA

- **Fase 1 — Descoberta e Desenho:** spec inicial (`docs/specs/SPEC-001-pipeline-vendas.md`)
  elaborada com apoio de IA (Claude), incluindo pesquisa do schema real do dataset Olist
  e validação de premissas com o responsável do projeto.
- **Fase 2 — Base de engenharia e IA:** estrutura de repositório, documentos de contexto
  de IA (`project-context.md`, `coding-rules.md`, `security-rules.md`,
  `testing-rules.md`), CI inicial e ADRs 001/002 gerados com apoio de IA e revisão
  humana.
- **Fase 3 — Construção iterativa:** implementação completa das 9 entidades (ingestão,
  qualidade, staging, data mart dimensional), script de simulação de batch diário e
  orquestração via Airflow — todas testadas com testes de integração reais (PostgreSQL
  e Airflow de verdade, não mockados). Vários bugs reais foram encontrados e corrigidos
  durante essa validação (ver `CHANGELOG.md`, seção "Corrigido").

## Regras de uso

Ver `docs/ai/security-rules.md` para classes de autonomia permitidas a agentes de IA
neste projeto, e `docs/ai/coding-rules.md`/`docs/ai/testing-rules.md` para os padrões
que toda geração de código deve seguir.

## Registro de decisões relevantes assistidas por IA

| Data | Decisão | Ferramenta | Validação humana |
|---|---|---|---|
| 2026-08 | Estrutura da spec inicial e schema do dataset Olist | Claude | Sim — premissas confirmadas em conversa |
| 2026-08 | Decisão de simular batch diário sobre dataset estático (ADR-002) | Claude | Sim — escolhido explicitamente pelo responsável do projeto |
| 2026-08 | PostgreSQL via Docker Compose | Claude | Sim — escolhido explicitamente pelo responsável do projeto |
| 2026-08 | Orquestração via Airflow, LocalExecutor (ADR-001) | Claude | Sim — decisão fechada explicitamente pelo responsável do projeto |
| 2026-08 | `dim_pagamento` agregada por pedido para evitar fan-out no fato | Claude | Sim — sinalizado como achado técnico antes de implementar |

## Limitações conhecidas desta implementação

- As DAGs do Airflow foram validadas rodando Airflow 2.9.3 diretamente (via
  `pip install apache-airflow` em ambiente isolado), não pela subida real dos
  containers via `docker compose` — Docker não estava disponível no ambiente onde o
  projeto foi construído. Validar `docker compose config` e um `up` real antes do
  primeiro uso em produção.
