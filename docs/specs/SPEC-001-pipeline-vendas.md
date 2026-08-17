# Pipeline de Analytics Engineering — Vendas E-commerce

> **Status:** Implementada (Fase 3 concluída — pipeline completo, ponta a ponta)
> **Spec ID:** SPEC-001-pipeline-vendas
> **Owner:** Fabio (Tech Lead / Desenvolvedor)
> **Metodologia:** Spec-Driven Development (SDD) — conforme `guia-desenvolvimento-assistido-por-ia.md`

---

## Contexto e problema

O projeto usa como fonte o dataset público **Brazilian E-Commerce Public Dataset by Olist** (Kaggle), contendo ~100 mil pedidos reais anonimizados, distribuídos em 9 arquivos CSV relacionados: `olist_customers_dataset`, `olist_orders_dataset`, `olist_order_items_dataset`, `olist_order_payments_dataset`, `olist_order_reviews_dataset`, `olist_products_dataset`, `olist_sellers_dataset`, `olist_geolocation_dataset` e `product_category_name_translation`.

O pipeline é desenhado como se esses arquivos chegassem diariamente de sistemas transacionais upstream (ERP, e-commerce), simulando um cenário real de ingestão recorrente — ainda que a fonte original seja um dataset histórico estático, essa decisão foi tomada deliberadamente para fins de demonstração de arquitetura de portfólio. Atualmente esses dados não passam por um processo estruturado de ingestão, validação e modelagem — o que impede análises confiáveis e consistentes no BI.

O problema a resolver: **construir o processo que produz dados confiáveis para análise**, não apenas analisar os dados manualmente a cada carga.

## Objetivo e não objetivos

**Objetivo:**
Construir um pipeline batch diário que ingere arquivos CSV/JSON de vendas, valida e transforma os dados, carrega em um Data Warehouse (PostgreSQL) em modelo dimensional (star schema), e disponibiliza um data mart pronto para consumo via Power BI.

**Não objetivos (fora de escopo nesta fase):**
- Ingestão em tempo real / streaming.
- Integração com APIs externas.
- Machine learning ou modelos preditivos sobre os dados de vendas.
- Multi-tenant ou múltiplas empresas/fontes simultâneas.
- Self-service data catalog completo (pode virar spec futura).

## Personas e fluxos

| Persona | Necessidade | Fluxo principal |
|---|---|---|
| Analista de BI | Consultar dados de vendas confiáveis e atualizados diariamente | Abre dashboard Power BI conectado ao data mart |
| Engenheiro de Dados (Fabio) | Rodar, monitorar e evoluir o pipeline | Executa/monitora pipeline, revisa logs e alertas de qualidade |
| Área de negócio | Tomar decisões baseadas em métricas de vendas e pedidos | Consome relatórios e dashboards derivados do data mart |

**Fluxo principal (E2E):**
1. Arquivos CSV das 9 entidades Olist chegam em um diretório de entrada (landing zone) — batch diário.
2. Pipeline Python detecta os arquivos, valida schema e qualidade dos dados de cada entidade.
3. Dados válidos são transformados (limpeza, tipagem, deduplicação, join entre entidades relacionadas) e carregados em staging no PostgreSQL.
4. Processo de modelagem dimensional popula o data mart (star schema) a partir das tabelas de staging.
5. Power BI consome o data mart via conexão direta/scheduled refresh.
6. Registros inválidos/rejeitados são isolados para reprocessamento ou investigação.

## Requisitos funcionais

- RF01: O pipeline deve detectar automaticamente novos arquivos CSV/JSON na landing zone.
- RF02: O pipeline deve validar schema (colunas obrigatórias, tipos) antes de processar cada arquivo.
- RF03: O pipeline deve aplicar regras de qualidade de dados (nulos críticos, duplicados, valores fora de faixa, chaves órfãs).
- RF04: Registros que falharem validação devem ser roteados para uma área de rejeitados (quarantine), com motivo do erro registrado.
- RF05: O pipeline deve carregar dados válidos em tabelas de staging no PostgreSQL.
- RF06: O pipeline deve popular o modelo dimensional (fato_vendas + dimensões: cliente, produto, loja, tempo, pagamento).
- RF07: Cargas devem ser idempotentes — reprocessar o mesmo arquivo não deve duplicar dados.
- RF08: O pipeline deve registrar logs estruturados de cada execução (início, fim, linhas processadas, linhas rejeitadas).
- RF09: Deve existir um mecanismo de notificação/alerta em caso de falha de execução.

## Requisitos não funcionais

### Segurança
- Acesso ao banco de dados via credenciais em secret manager (nunca em código ou `.env` versionado).
- Autorização mínima: usuário de serviço do pipeline só tem permissão de escrita nas tabelas de staging e data mart, sem privilégios administrativos.
- Arquivos de entrada tratados como não confiáveis: validação e sanitização obrigatórias antes de qualquer processamento.

### Privacidade/LGPD
- O dataset já é publicado anonimizado pela Olist (identificadores de cliente/vendedor são hashes, não nomes reais; texto de reviews teve referências a empresas removidas). Mesmo assim, tratar `customer_id`/`customer_unique_id` como identificador pseudonimizado, sem tentativa de reidentificação.
- Não há necessidade de mascaramento adicional nesta fase, mas a distinção entre dado pseudonimizado (ainda dado pessoal sob LGPD) e dado anônimo deve constar na documentação do projeto.

### Disponibilidade e recuperação
- Pipeline deve suportar reprocessamento manual de um dia específico sem intervenção complexa.
- Falha em um arquivo (de uma das 9 entidades) não pode interromper o processamento dos demais arquivos do batch.

### Desempenho e capacidade
- Volume de referência: ~100.000 pedidos, ~112.000 itens de pedido, distribuídos entre as 9 tabelas — volume compatível com processamento em Pandas puro, sem necessidade de engines distribuídas nesta fase.
- Suportar crescimento incremental de volume sem redesenho arquitetural nos próximos 12 meses.

### Observabilidade
- Logs estruturados com timestamp, arquivo processado, linhas válidas/rejeitadas, duração.
- Métricas mínimas: taxa de sucesso de execução, volume processado por dia, taxa de rejeição.
- Alerta acionável quando taxa de rejeição ultrapassar limiar definido ou execução falhar.

### Custos e limites
- Uso de infraestrutura local/Docker nesta fase — sem custo de cloud gerenciada.
- Definir limite de tamanho de arquivo aceito por execução (evitar OOM em processamento com Pandas).

## Critérios de aceitação verificáveis

- [x] Dado um arquivo CSV válido na landing zone, quando o pipeline executa, então os dados aparecem corretamente no data mart em até N minutos.
      Validado ponta a ponta (`tests/integration/test_run_pipeline.py`, DAGs testadas via Airflow real). **"N minutos" nunca foi quantificado** — não há SLA de tempo definido nem medido; para o volume do projeto (~100k pedidos), a execução observada foi da ordem de segundos, mas isso não foi testado sob carga real.
- [x] Dado um arquivo com linhas inválidas (ex.: cliente_id nulo), quando processado, então essas linhas são isoladas na quarentena com motivo registrado, e as linhas válidas seguem o fluxo normal.
      Validado por `src/quality/*` + `write_rejected` + testes unitários de cada entidade (ex.: `test_purchase_timestamp_ausente_e_rejeitado`).
- [x] Dado que o mesmo arquivo é processado duas vezes, quando o pipeline executa novamente, então não há duplicação de registros no data mart (idempotência).
      Validado com testes de integração reais contra PostgreSQL: `test_recarregar_o_mesmo_order_id_atualiza_em_vez_de_duplicar`, `test_customer_sk_e_estavel_entre_cargas_repetidas`, `test_recarregar_fact_pedidos_no_mesmo_item_atualiza_em_vez_de_duplicar`.
- [ ] Dado um arquivo malformado (schema incompatível), quando o pipeline tenta processá-lo, então a execução falha de forma controlada, sem corromper dados já carregados, e um alerta é disparado.
      **Parcialmente atendido.** "Falha controlada, sem corromper dados já carregados": sim — `SchemaValidationError` interrompe só aquele arquivo (`validate_schema`, testado). "Um alerta é disparado": **não implementado** — hoje só há `logger.error`/`logger.warning`, sem nenhum mecanismo de alerta real (e-mail, Slack, PagerDuty, etc.). Gap real, não hipotético; ver `docs/ai/project-context.md` para status atualizado.
- [x] Dado o data mart populado, quando o Power BI conecta, então as métricas de vendas (total, por produto, por loja, por período) batem com os dados de origem.
      Views de consumo criadas (`src/loading/reporting_views.py`: `vw_vendas_por_produto`, `vw_vendas_por_vendedor`, `vw_vendas_por_periodo`, `vw_resumo_pedidos`) e validadas com dados reais batendo contra a origem (`tests/integration/test_reporting_views.py`). **A conexão real com o Power BI Desktop não foi testada** (ferramenta proprietária, indisponível no ambiente de desenvolvimento) — guia de conexão em `docs/runbooks/conexao_powerbi.md`.

## Casos de erro e borda

- Arquivo ausente no horário esperado do batch diário.
- Arquivo corrompido ou não parseável (CSV malformado, JSON inválido).
- Schema alterado pela origem sem aviso (coluna nova, coluna removida, tipo alterado).
- Chaves estrangeiras órfãs (ex.: venda referenciando produto inexistente).
- Duplicidade de registros dentro do mesmo arquivo ou entre execuções.
- Datas fora de faixa plausível (ex.: vendas com data futura).
- Volume de arquivo muito acima do esperado (possível erro de origem).

## Contratos de dados

**Entrada (9 arquivos CSV — dataset Olist, colunas exatas a confirmar linha a linha na Fase 2 com os arquivos baixados):**
```
olist_orders_dataset.csv          — pedido core: order_id, customer_id, order_status, timestamps (compra, aprovação, entrega)
olist_order_items_dataset.csv     — itens do pedido: order_id, product_id, seller_id, price, freight_value
olist_order_payments_dataset.csv  — pagamentos: order_id, payment_type, payment_installments, payment_value
olist_order_reviews_dataset.csv   — avaliações: review_id, order_id, review_score, comentários
olist_customers_dataset.csv       — clientes: customer_id, customer_unique_id, customer_zip_code_prefix, city, state
olist_products_dataset.csv        — produtos: product_id, categoria, dimensões/peso
olist_sellers_dataset.csv         — vendedores: seller_id, seller_zip_code_prefix, city, state
olist_geolocation_dataset.csv     — geolocalização por CEP: zip_code_prefix, lat, lng, city, state
product_category_name_translation.csv — tradução de categoria (PT-BR → EN)
```

**Saída (modelo dimensional):**
```
fato_pedidos (order_id, cliente_sk, produto_sk, vendedor_sk, tempo_sk, pagamento_sk, quantidade, valor_item, valor_frete, review_score)
dim_cliente, dim_produto, dim_vendedor, dim_tempo, dim_pagamento, dim_geolocalizacao
```

> A tabela de fato foi renomeada de `fato_vendas` para `fato_pedidos` para refletir a granularidade real do dataset (pedido → itens), e o contrato final deve ser validado contra os arquivos baixados na Fase 2.

## Decisões de arquitetura e restrições

```text
CSV / JSON (landing zone)
        │
        ▼
Python ETL (validação + transformação)
        │
        ▼
PostgreSQL — Staging
        │
        ▼
Data Mart — Star Schema
        │
        ▼
Power BI
```

- Stack: Python, Pandas, SQL, PostgreSQL (via Docker Compose), Docker, Power BI, Git/GitHub — consistente com o restante do portfólio.
- Componente adicional de particionamento: script que quebra o dataset histórico por `order_purchase_timestamp`, simulando lotes diários na landing zone — tratado como parte do pipeline, com testes próprios.
- Orquestração do batch diário a definir na Fase 2 (opções: cron simples, Airflow, ou orquestrador leve — decisão vira ADR).
- Modelagem dimensional (star schema) escolhida por ser o padrão consolidado para consumo em BI.

## Estratégia de testes

- Unitários: funções de validação de schema, regras de qualidade de dados, transformações (ex.: cálculo de valor_total).
- Integração: carga completa de um arquivo de amostra até o data mart, usando banco de teste.
- Contrato: validação de que o schema de saída do data mart não quebra o modelo esperado pelo Power BI.
- Dados: testes com arquivos "sujos" propositalmente (nulos, duplicados, tipos errados) para validar tratamento de erro.
- Regressão: todo bug de qualidade de dados encontrado em produção vira um caso de teste.

## Estratégia de rollout e rollback

- Rollout: iniciar com processamento em paralelo (shadow) comparando contra qualquer processo manual existente, antes de promover o data mart como fonte oficial do BI.
- Rollback: manter staging e data mart versionados por data de carga, permitindo reverter para o estado do dia anterior caso uma carga corrompa dados.
- Reprocessamento: capacidade de re-rodar um dia específico de forma idempotente é requisito de rollback funcional (ver RF07).

## Riscos, premissas e dependências

**Premissas confirmadas:**
- Volume: ~100k pedidos, dataset Olist, escala compatível com Pandas puro.
- PII: dados já anonimizados pela Olist; tratar `customer_id`/`customer_unique_id` como pseudonimizado.
- Schema: 9 entidades confirmadas (ver Contratos de dados); colunas exatas a validar linha a linha na Fase 2.
- PostgreSQL sobe via Docker Compose neste próprio projeto, mantendo o padrão de "ambiente reproduzível" do portfólio.
- Simulação de "batch diário": um script auxiliar particiona o dataset histórico por `order_purchase_timestamp`, gerando um lote de arquivos por dia simulado, para que o pipeline seja exercitado como se fosse ingestão incremental real.

**Riscos:**
- Como o dataset é histórico (2016–2018) e estático, simular "chegada diária" é uma decisão deliberada de design para fins de portfólio — deixar isso explícito na documentação evita confusão futura sobre a natureza dos dados.
- Mudança de schema real dos CSVs em relação ao esperado (a confirmar na Fase 2, ao baixar os arquivos).
- O script de particionamento por data é, ele próprio, um componente do pipeline e precisa de teste/validação (ex.: garantir que nenhum registro seja perdido ou duplicado ao particionar).

**Dependências:**
- Download dos 9 arquivos CSV do Kaggle (`kaggle datasets download -d olistbr/brazilian-ecommerce`) para a landing zone do projeto.
- Docker e Docker Compose instalados no ambiente de desenvolvimento.

---

## Próximos passos (Fase 1 → Fase 2 do roteiro)

> Todos os itens abaixo foram concluídos — seção mantida como registro histórico
> do planejamento original. Status atual do projeto: `docs/ai/project-context.md`.

1. ✅ Baixar os 9 arquivos CSV do Kaggle para a landing zone e validar colunas exatas contra o contrato de dados.
2. ✅ Registrar ADR da decisão de orquestração do batch (cron vs. Airflow vs. outro) e ADR do script de particionamento por data.
3. ✅ Criar estrutura de repositório (`docs/specs`, `docs/adr`, `docs/ai`, `src`, `tests`, `infra`) conforme padrão do guia.
4. ✅ Escrever `project-context.md`, `coding-rules.md` e `testing-rules.md` para orientar a implementação assistida por IA.
5. ✅ Criar `docker-compose.yml` para o PostgreSQL local (hoje na raiz do repo, com Postgres + app + Airflow completos).
