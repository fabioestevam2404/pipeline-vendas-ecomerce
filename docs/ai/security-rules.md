# Regras de Segurança — Pipeline de Vendas E-commerce

## Dados

- O dataset Olist é publicado anonimizado, mas `customer_id`/`customer_unique_id` e
  `seller_id` são tratados como identificadores pseudonimizados — dado pessoal sob LGPD
  em sentido amplo, mesmo sem nome/e-mail real.
- Nenhum dado do dataset deve ser enviado a ferramentas de IA externas não aprovadas
  além do necessário para depuração pontual, e nunca em volume (linhas completas de
  clientes) — usar amostras sintéticas equivalentes quando precisar exemplificar algo
  em prompt.
- Arquivos CSV de entrada são tratados como não confiáveis: validação de schema e
  sanitização são obrigatórias antes de qualquer processamento (ver RF02/RF03 da spec).

## Segredos

- Credenciais do PostgreSQL vivem exclusivamente em `.env` local (não versionado) ou
  em secret manager, nunca em `docker-compose.yml`, código, teste, log ou documentação.
- `.env.example` deve conter apenas nomes de variáveis, nunca valores reais.

## Acesso e autorização

- O usuário de banco usado pelo pipeline tem permissão apenas de leitura/escrita nas
  tabelas de staging e data mart — sem privilégios de administração do PostgreSQL.
- Ambiente local via Docker Compose não deve expor a porta do PostgreSQL além do
  necessário para desenvolvimento (evitar `0.0.0.0` em produção futura, caso o projeto
  evolua para deploy real).

## Dependências

- Fixar versões no `requirements.txt`/`pyproject.toml`.
- Rodar scanner de dependências (SCA) no CI antes de qualquer merge (ver
  `.github/workflows/ci.yml`).

## Classe de autonomia de agentes de IA neste projeto

Conforme a matriz de autonomia do guia (seção 5.3):

| Classe | Permitido neste projeto? |
|---|---|
| Observação | Sim — ler código, logs, specs, propor plano |
| Proposição | Sim — criar diffs, testes, documentação; requer aprovação humana antes de merge |
| Execução controlada | Sim — rodar testes locais/sandbox, abrir PR; requer aprovação para ações fora do sandbox |
| Execução privilegiada | **Proibida** — nenhum agente altera o banco de produção/dados carregados diretamente, sem gate explícito |

Como este é um projeto de portfólio sem ambiente de produção real, "execução
privilegiada" aqui equivale a: alterar dados já carregados no data mart, ou publicar
artefatos fora do repositório local, sem revisão humana.
