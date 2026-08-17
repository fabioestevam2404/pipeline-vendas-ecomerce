# Regras de Teste — Pipeline de Vendas E-commerce

## Pirâmide aplicada a este projeto

- **Unitários** (`tests/unit`): regras de validação de schema, regras de qualidade de
  dados (nulos, duplicados, chaves órfãs), funções de transformação isoladas.
- **Integração** (`tests/integration`): carga completa de um arquivo de amostra até o
  staging/data mart, usando um PostgreSQL de teste (container efêmero).
- **Contrato** (`tests/contract`): schema de saída do data mart não pode quebrar sem
  atualização explícita da spec e do contrato de dados.
- **E2E** (`tests/e2e`): um dia simulado completo, das 9 entidades até o data mart,
  validando que os totais batem com a origem. Usado com parcimônia (mais lento).

## Regras para testes gerados por IA

- Todo teste deve exercitar comportamento real, não apenas confirmar um mock.
- Testes de validação de qualidade **devem incluir casos negativos**: arquivo com
  `cliente_id` nulo, `order_id` duplicado, `product_id` órfão, data de pedido futura.
- Não aceitar teste que apenas eleva cobertura sem verificar resultado (ex.: chamar a
  função e só checar que não lançou exceção, sem checar o valor retornado).
- Todo bug de qualidade de dados encontrado durante o desenvolvimento vira um caso de
  teste de regressão antes de ser corrigido.

## Dados de teste

- Usar uma amostra fixa e pequena (poucas dezenas de linhas) de cada uma das 9
  entidades Olist como fixture, cobrindo casos válidos e inválidos deliberadamente.
- Nunca usar o dataset completo (~100k pedidos) em testes unitários — reservar para
  o teste E2E, e mesmo assim considerar uma amostra representativa se a duração for
  um problema.

## Cobertura mínima esperada

- `src/quality` e `src/transformation`: cobertura alta (funções puras, fáceis de testar
  exaustivamente).
- `src/ingestion` e `src/loading`: cobertura via testes de integração (dependem de I/O).

## Critérios de aceitação como fonte de teste

Cada critério de aceitação verificável da spec (`SPEC-001-pipeline-vendas.md`, seção
"Critérios de aceitação verificáveis") deve ter pelo menos um teste automatizado
correspondente antes de a funcionalidade ser considerada pronta.
