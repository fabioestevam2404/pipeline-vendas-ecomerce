# ADR-002: Simulação de batch diário sobre dataset histórico estático

## Status
Aceito

## Contexto
O dataset fonte (Olist, Kaggle) é histórico e estático (pedidos de 2016–2018), não um
feed real de chegada diária. O objetivo do projeto, porém, é demonstrar uma arquitetura
de pipeline de ingestão recorrente para fins de portfólio.

## Decisão
Manter o desenho de "batch diário" de forma deliberada. Um script auxiliar
(`scripts/simulate_daily_batches.py`) particiona o dataset completo por
`order_purchase_timestamp`, gerando lotes de arquivos que simulam chegadas diárias na
landing zone. O pipeline em si (ingestão → qualidade → transformação → carga) é
agnóstico a essa simulação e trataria uma chegada real da mesma forma.

## Alternativas consideradas
- **Carga única (full load histórico):** mais simples, mas não demonstra a capacidade
  de reprocessamento incremental nem os mecanismos de idempotência do pipeline.
- **Deixar ambíguo:** rejeitado por risco de gerar confusão futura sobre a natureza dos
  dados (real-time vs. simulação).

## Consequências
- Positivo: o pipeline demonstra idempotência, reprocessamento por dia e tratamento de
  falha parcial de forma realista.
- Negativo: exige documentação clara (feita em `project-context.md` e nesta ADR) para
  que ninguém confunda a simulação com um cenário de produção real.

## Segurança, privacidade e compliance
Nenhum impacto adicional — o particionamento não altera a classificação dos dados.

## Observabilidade e operação
Logs do script de particionamento devem indicar claramente que se trata de dado
simulado (prefixo `[SIMULACAO]` ou campo equivalente nos logs estruturados).

## Migração e rollback
N/A — decisão de design, não de dado em produção.

## Referências
- `docs/specs/SPEC-001-pipeline-vendas.md`
