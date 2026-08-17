# ADR-001: Orquestração do batch diário

## Status
Aceito

## Contexto
O pipeline precisa executar diariamente (de forma simulada) uma sequência de etapas:
particionamento → ingestão → qualidade → transformação → carga. É preciso decidir a
forma de orquestração para o escopo deste projeto de portfólio.

## Decisão
Usar **Apache Airflow**, executado via um serviço adicional no `docker-compose.yml`
(imagem oficial `apache/airflow`, com um `LocalExecutor` e o mesmo PostgreSQL do
projeto servindo de metastore do Airflow, em schema separado). Cada etapa do pipeline
(particionamento → ingestão → qualidade → transformação → carga) vira uma task de uma
única DAG diária.

## Alternativas consideradas
1. **Cron simples** rodando um script Python orquestrador — mais simples, mas sem UI,
   histórico de execução ou observabilidade nativa; exige construir esses recursos
   manualmente para atender aos requisitos de observabilidade da spec.
2. **Orquestrador leve (ex.: Prefect local)** — meio-termo razoável, mas com menor valor
   demonstrativo para portfólio, já que Airflow é mais reconhecido no mercado de dados.
3. **Airflow** (escolhido) — maior complexidade inicial de setup, compensada por UI de
   execuções, retries nativos, histórico e alinhamento com os requisitos de
   observabilidade (RF08, RF09 da spec) e com o restante do roadmap de DataOps do autor.

## Consequências
- Positivo: observabilidade e retries nativos; cada etapa do pipeline vira uma task
  isolada e testável; portfólio ganha peso demonstrativo em orquestração de dados.
- Negativo: aumenta a superfície de configuração (metastore, scheduler, webserver);
  exige atenção extra em `security-rules.md` para não expor a UI do Airflow sem
  autenticação, mesmo em ambiente local.
- Ação decorrente: ✅ concluída — `docker-compose.yml` (hoje na raiz do repo, não mais
  em `infra/`) tem os serviços do Airflow (webserver, scheduler, init); as DAGs foram
  criadas em `dags/`, seguindo a convenção registrada em `coding-rules.md`.

## Segurança, privacidade e compliance
A UI do Airflow deve ter autenticação habilitada mesmo em ambiente local (usuário/senha
via `.env`, nunca hardcoded). Nenhuma credencial de banco deve aparecer em variáveis de
conexão do Airflow expostas na UI.

## Observabilidade e operação
Airflow passa a ser a fonte primária de observabilidade de execução do pipeline
(sucesso/falha por task, duração, retries). Os logs estruturados definidos em
`coding-rules.md` continuam existindo dentro de cada task, complementando — não
substituindo — os logs nativos do Airflow.

## Migração e rollback
Se a complexidade do Airflow se mostrar desproporcional ao escopo do projeto, a
migração para a Alternativa 1 (cron) é reversível: as tasks já isoladas por etapa podem
ser chamadas por um script orquestrador simples sem reescrever a lógica de negócio.

## Referências
- `docs/specs/SPEC-001-pipeline-vendas.md`
- ADR-002 (simulação de batch diário)
