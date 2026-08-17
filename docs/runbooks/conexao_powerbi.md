# Runbook — Conectando o Power BI ao Data Mart

> **Nota de transparência:** este guia foi escrito com base na documentação
> oficial do conector PostgreSQL do Power BI e na estrutura real do schema
> `mart` deste projeto (validada com testes de integração reais — ver
> `tests/integration/test_reporting_views.py`). **A conexão em si não foi
> testada contra o Power BI Desktop de verdade** — essa ferramenta é
> proprietária, roda apenas em Windows/macOS via aplicativo desktop, e não
> está disponível no ambiente onde este projeto foi construído. O que está
> validado de verdade: as views abaixo existem, retornam dados corretos e
> batem com a origem (critério de aceitação da spec, seção "Critérios de
> aceitação verificáveis").

## Pré-requisito

Driver **Npgsql** instalado (o conector nativo do Power BI para PostgreSQL
depende dele) — ver
[documentação oficial do conector PostgreSQL](https://learn.microsoft.com/power-query/connectors/postgresql).

## O que conectar: views, não as tabelas do fato/dimensões diretamente

O schema `mart` expõe as tabelas normalizadas (`fact_pedidos`, `dim_customers`,
`dim_products`, `dim_sellers`, `dim_tempo`, `dim_pagamento`) e quatro **views
de consumo** já agregadas, pensadas especificamente para BI
(`src/loading/reporting_views.py`):

| View | Grão | Uso típico no Power BI |
|---|---|---|
| `mart.vw_vendas_por_produto` | 1 linha por produto | Ranking de produtos, categoria mais vendida |
| `mart.vw_vendas_por_vendedor` | 1 linha por vendedor | Ranking de vendedores, análise geográfica |
| `mart.vw_vendas_por_periodo` | 1 linha por data | Série temporal, sazonalidade, fim de semana vs. dia útil |
| `mart.vw_resumo_pedidos` | 1 linha por pedido | Ticket médio, forma de pagamento, satisfação (review) |

**Recomendação:** para dashboards que só precisam de métricas agregadas
(a maioria), conecte nas views — menos dado trafegado, refresh mais rápido.
Para análises que precisam do grão de item de pedido (ex.: "quais produtos
são comprados juntos"), conecte em `mart.fact_pedidos` + as dimensões e monte
o modelo relacional dentro do próprio Power BI.

## Passo a passo (Power BI Desktop)

1. **Obter Dados** → **Banco de dados** → **PostgreSQL database**.
2. **Servidor:** `localhost` (ou o host onde o container `postgres` está
   exposto — `127.0.0.1:${POSTGRES_PORT}` no setup local via Docker, ver
   `docker-compose.yml`).
3. **Banco de dados:** valor de `POSTGRES_DB` no seu `.env` (padrão:
   `vendas_ecommerce`).
4. **Modo de conectividade de dados:**
   - **Import** — mais simples, bom para o volume deste projeto (~100k
     pedidos). Requer refresh manual/agendado para ver dados novos.
   - **DirectQuery** — sempre atualizado, mas cada interação no relatório
     gera uma query no Postgres. Recomendado se o pipeline rodar com
     frequência (ex.: via Airflow `@daily`) e você quiser o dashboard sempre
     refletindo o último `batch_date` carregado.
5. Autenticação: usuário/senha = `POSTGRES_USER`/`POSTGRES_PASSWORD` do
   `.env` (nunca commitados — ver `docs/ai/security-rules.md`).
6. No **Navegador**, selecione o schema `mart` e marque as views/tabelas
   desejadas.
7. Se importar as tabelas normalizadas (não as views), monte os
   relacionamentos no **Modelo** do Power BI:
   - `fact_pedidos[customer_sk]` → `dim_customers[customer_sk]`
   - `fact_pedidos[produto_sk]` → `dim_products[product_sk]`
   - `fact_pedidos[vendedor_sk]` → `dim_sellers[seller_sk]`
   - `fact_pedidos[date_sk]` → `dim_tempo[date_sk]`
   - `fact_pedidos[pagamento_sk]` → `dim_pagamento[pagamento_sk]`
   - Todos os relacionamentos são 1:N (dimensão → fato), lado "1" nas
     dimensões — cardinalidade padrão que o Power BI já infere corretamente
     na maioria dos casos, mas vale conferir manualmente.

## Validando que os números batem (o critério de aceitação da spec)

Depois de conectar, compare uma métrica simples do Power BI com uma query
direta no banco, para confirmar que a conexão está correta:

```sql
-- Receita total — deve bater com o cartão/visual de "receita total" no relatório
SELECT SUM(receita_total) FROM mart.vw_vendas_por_produto;

-- Contagem de pedidos distintos — deve bater com uma medida COUNT(DISTINCT order_id)
SELECT COUNT(DISTINCT order_id) FROM mart.fact_pedidos;
```

Isso é exatamente o que `tests/integration/test_reporting_views.py` já prova
de forma automatizada — a query acima é a mesma lógica, só que rodada
manualmente contra o Power BI em vez de contra `pytest`.

## Medidas DAX sugeridas (ponto de partida)

```dax
Receita Total = SUM(vw_vendas_por_produto[receita_total])
Ticket Médio = DIVIDE([Receita Total], DISTINCTCOUNT(vw_resumo_pedidos[order_id]))
Taxa de Frete = DIVIDE(SUM(vw_vendas_por_produto[frete_total]), [Receita Total])
Nota Média de Review = AVERAGE(vw_resumo_pedidos[review_score])
```

## Se os números não baterem

- Confira se o pipeline rodou até o fim para o `batch_date` que você espera
  ver (`SELECT DISTINCT batch_date FROM mart.fact_pedidos ORDER BY 1;`).
- Views são `CREATE OR REPLACE`, recriadas a cada execução do pipeline
  (`create_reporting_views`, chamada em `scripts/run_pipeline.py` e nas duas
  DAGs) — nunca ficam desatualizadas em relação ao schema, mas os DADOS
  dependem de o fato/dimensões terem sido carregados para o período.
- Se usou modo **Import**, lembre de dar refresh manual (ou configurar
  refresh agendado) — o Power BI não reflete mudanças no banco
  automaticamente nesse modo.
