# Regras de Código — Pipeline de Vendas E-commerce

> Regras normativas e testáveis. Toda geração de código por IA deve seguir estas regras
> e referenciar `SPEC-001-pipeline-vendas.md`.

## Estrutura e modularidade

- Arquivos limitados a ~250 linhas; se ultrapassar, dividir em módulos coesos.
- Um módulo, uma responsabilidade: validação, transformação e carga vivem em pastas
  separadas (`src/quality`, `src/transformation`, `src/loading`), nunca misturadas.
- Funções devem ter assinatura tipada (type hints obrigatórios em todo código novo).

## Padrões de nomenclatura

- Nomes em português para conceitos de negócio (`fato_pedidos`, `dim_cliente`) e em
  inglês para nomes técnicos de função/variável (`load_staging`, `validate_schema`).
- Nenhuma abreviação obscura — preferir clareza a brevidade.

## Tratamento de erros

- Toda função de I/O (leitura de arquivo, escrita no banco) deve tratar exceções
  explicitamente — nunca `except Exception: pass`.
- Erros de validação de dados **não são exceções fatais**: devem ser capturados,
  registrados com motivo, e o registro roteado para quarentena (ver RF04 da spec).
- Erros de infraestrutura (banco indisponível, arquivo corrompido de forma irrecuperável)
  **são fatais**: devem interromper a execução daquele arquivo especificamente, sem
  interromper o processamento dos demais arquivos do batch.

## Logging

- Logs estruturados (JSON) com: timestamp, nome do arquivo/entidade, etapa do pipeline,
  linhas processadas, linhas rejeitadas, duração.
- Nunca logar conteúdo completo de linha de dado (mesmo pseudonimizado) — logar apenas
  identificadores e contadores.
- Um logger por módulo, nomeado com o path do módulo.

## Consultas ao banco

- Toda consulta usa SQLAlchemy Core ou parametrização explícita — proibida concatenação
  de string com dado de entrada.
- Cargas devem ser idempotentes: usar `UPSERT`/`ON CONFLICT` ou truncar+recarregar a
  partição do dia simulado, nunca `INSERT` cego (ver RF07 da spec).

## Segredos e configuração

- Nenhuma credencial de banco em código, teste ou log — usar variáveis de ambiente
  carregadas a partir de `.env` (nunca versionado; ver `.env.example`).
- Configuração de conexão centralizada em um único módulo (`src/config.py`), nunca
  hardcoded em múltiplos arquivos.

## Testes obrigatórios junto do código

- Toda função de validação/transformação nova vem acompanhada de teste unitário
  cobrindo caso feliz + pelo menos um caso de borda (ver `docs/ai/testing-rules.md`).
- Não aceitar código gerado por IA sem os testes correspondentes no mesmo PR.

## O que a IA não deve fazer neste projeto

- Não inventar colunas do dataset Olist — usar apenas os contratos definidos na spec
  ou colunas confirmadas nos arquivos reais baixados.
- Não sugerir bibliotecas fora da stack homologada sem justificativa e ADR.
- Não gerar migrações de banco que alterem dados de staging/data mart já carregados
  sem estratégia de rollback explícita.
