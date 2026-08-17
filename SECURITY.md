# Política de Segurança

## Escopo
Este é um projeto de portfólio pessoal usando dados públicos anonimizados (dataset
Olist). Não há dados de produção reais nem clientes reais envolvidos.

## Segredos
- Nenhuma credencial deve ser commitada. Use `.env` local (ver `.env.example`).
- Se um segredo for commitado por engano, considere-o comprometido: revogue/rotacione
  e remova do histórico do git.

## Dependências
- Dependências são verificadas no CI via `pip-audit`.
- Vulnerabilidades críticas bloqueiam merge (ver `.github/workflows/ci.yml`).

## Dados
- O dataset fonte já é anonimizado pela Olist. Ainda assim, identificadores de
  cliente/vendedor são tratados como pseudonimizados — ver `docs/ai/security-rules.md`.

## Reportar um problema
Como projeto de portfólio individual, não há processo formal de disclosure — abra uma
issue no repositório caso identifique algo relevante.
