# Guia de Contribuição

Este projeto segue a metodologia de Desenvolvimento Assistido por IA (DAI) descrita em
`docs/ai/`. Antes de contribuir (humano ou com apoio de IA):

1. Toda mudança relevante parte de uma spec (`docs/specs/`) ou de uma alteração
   registrada nela. Sem spec, sem implementação.
2. Decisões arquiteturais significativas geram um ADR (`docs/adr/`, template em
   `docs/adr/TEMPLATE.md`).
3. Leia `docs/ai/project-context.md`, `docs/ai/coding-rules.md`,
   `docs/ai/security-rules.md` e `docs/ai/testing-rules.md` antes de gerar código com IA.
4. Toda mudança de código vem com testes correspondentes (ver `docs/ai/testing-rules.md`).
5. Pull requests seguem o template em `.github/pull_request_template.md`, incluindo a
   seção de assistência por IA quando aplicável.
6. Nenhum merge sem os gates do CI aprovados (lint, testes, secret scanning, SCA).

## Setup local

```bash
cp .env.example .env   # preencha as variáveis
./validate_docker.sh   # checagem estática (sintaxe, lint) antes de subir containers
docker compose up -d postgres
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit tests/integration
```

Ver `README.md`, seção "Docker", para o setup completo (incluindo Airflow) e
`docs/runbooks/validacao_docker.md` para rodar tudo dentro de containers via
`docker compose exec app ...`.
