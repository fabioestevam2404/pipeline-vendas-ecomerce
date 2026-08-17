# Build multi-stage: instala dependências num estágio, copia só o resultado
# para a imagem final — reduz superfície e tamanho da imagem de runtime.
# Context de build: raiz do repositório (`docker build -t pipeline-vendas:latest .`
# ou via `docker-compose.yml`, serviço `app`).

# --- Stage 1: builder ---------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt -r requirements-dev.txt

# --- Stage 2: runtime -----------------------------------------------------
FROM python:3.11-slim AS runtime

# Menor privilégio (docs/ai/security-rules.md): usuário de serviço dedicado,
# nunca root — mesmo padrão já usado no projeto de MLOps do portfólio.
RUN groupadd --gid 1000 pipeline \
    && useradd --uid 1000 --gid pipeline --shell /bin/bash --create-home pipeline

COPY --from=builder /root/.local /home/pipeline/.local

ENV PATH=/home/pipeline/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
RUN chown pipeline:pipeline /app

COPY --chown=pipeline:pipeline src/ ./src/
COPY --chown=pipeline:pipeline scripts/ ./scripts/
COPY --chown=pipeline:pipeline dags/ ./dags/
COPY --chown=pipeline:pipeline pytest.ini ./

# Diretórios de dados montados via volume em runtime (ver docker-compose.yml)
# — criados aqui só para garantir que existem mesmo sem bind mount.
RUN mkdir -p /app/data/raw /app/data/landing /app/data/quarantine \
    && chown -R pipeline:pipeline /app/data

USER 1000:1000

# Sem CMD fixo de produção: este container é usado via `docker compose run`
# para comandos ad-hoc (scripts, testes) — ver README.md, seção Docker.
# O padrão abre um shell interativo quando rodado sem argumentos.
CMD ["/bin/bash"]
