#!/usr/bin/env bash
# Valida o setup Docker do projeto antes de um `docker compose up` real.
#
# O que este script FAZ verificar (sem precisar do daemon Docker rodando):
#   - Presença de docker/docker compose no PATH.
#   - Existência do .env (a partir de .env.example) com as variáveis
#     obrigatórias preenchidas.
#   - Sintaxe e interpolação do docker-compose.yml via `docker compose config`.
#   - Lint dos Dockerfiles via hadolint, se disponível.
#
# O que este script NÃO faz (requer o daemon Docker de verdade):
#   - Build das imagens.
#   - Subida dos containers / healthchecks reais.
#   - Execução da suíte de testes dentro do container.
# Rode `docker compose up airflow-init` e depois `docker compose up -d`
# manualmente para validar isso — este script é a checagem RÁPIDA que roda
# antes disso, não um substituto. Ver docs/runbooks/validacao_docker.md para
# o passo a passo completo, com critérios de aceite.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"

PASSOS_OK=0
PASSOS_FALHOS=0

ok() {
    echo "  ✅ $1"
    PASSOS_OK=$((PASSOS_OK + 1))
}

falha() {
    echo "  ❌ $1"
    PASSOS_FALHOS=$((PASSOS_FALHOS + 1))
}

aviso() {
    echo "  ⚠️  $1"
}

echo "=== 1. Ferramentas necessárias ==="
if command -v docker >/dev/null 2>&1; then
    ok "docker encontrado: $(docker --version)"
    DOCKER_DISPONIVEL=1
else
    falha "docker não encontrado no PATH — instale antes de continuar"
    DOCKER_DISPONIVEL=0
fi

if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
    ok "docker-compose (standalone) encontrado"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    ok "docker compose (plugin) encontrado"
else
    falha "nem 'docker compose' nem 'docker-compose' foram encontrados"
    COMPOSE_CMD=""
fi

echo ""
echo "=== 2. Arquivo .env ==="
if [ ! -f "$ENV_FILE" ]; then
    aviso ".env não existe — copiando de .env.example"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    aviso "Preencha POSTGRES_PASSWORD, AIRFLOW_ADMIN_PASSWORD e AIRFLOW_FERNET_KEY em .env antes de continuar"
fi

VARIAVEIS_OBRIGATORIAS=(POSTGRES_PASSWORD AIRFLOW_ADMIN_PASSWORD AIRFLOW_FERNET_KEY)
for var in "${VARIAVEIS_OBRIGATORIAS[@]}"; do
    valor="$(grep -E "^${var}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2-)"
    if [ -z "$valor" ]; then
        falha "$var está vazio em .env — preencha antes de subir os containers"
    else
        ok "$var está preenchido"
    fi
done

echo ""
echo "=== 3. Sintaxe do docker-compose.yml ==="
if [ -n "$COMPOSE_CMD" ]; then
    if $COMPOSE_CMD -f "$COMPOSE_FILE" config -q 2>/tmp/compose_config_erro; then
        ok "docker-compose.yml válido (sintaxe + interpolação)"
    else
        falha "docker-compose.yml inválido:"
        cat /tmp/compose_config_erro
    fi
else
    aviso "Pulado — nenhuma ferramenta de compose disponível"
fi

echo ""
echo "=== 4. Lint dos Dockerfiles (hadolint) ==="
if command -v hadolint >/dev/null 2>&1; then
    ROTULO_DOCKERFILE_APP="Dockerfile (app)"
    ROTULO_DOCKERFILE_AIRFLOW="infra/airflow/Dockerfile"
    declare -A ROTULOS=(
        ["${SCRIPT_DIR}/Dockerfile"]="$ROTULO_DOCKERFILE_APP"
        ["${SCRIPT_DIR}/infra/airflow/Dockerfile"]="$ROTULO_DOCKERFILE_AIRFLOW"
    )
    for dockerfile in "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/infra/airflow/Dockerfile"; do
        rotulo="${ROTULOS[$dockerfile]}"
        if hadolint "$dockerfile" 2>/tmp/hadolint_erro; then
            ok "${rotulo} sem apontamentos"
        else
            falha "${rotulo} com apontamentos:"
            cat /tmp/hadolint_erro
        fi
    done
else
    aviso "hadolint não encontrado — pulando lint de Dockerfile (não bloqueante)"
    aviso "Instale via: https://github.com/hadolint/hadolint#install"
fi

echo ""
echo "=== 5. Passos que exigem o daemon Docker (não executados aqui) ==="
if [ "$DOCKER_DISPONIVEL" = "1" ] && docker info >/dev/null 2>&1; then
    aviso "Daemon Docker está rodando — você pode prosseguir com:"
    echo "      $COMPOSE_CMD -f $COMPOSE_FILE build"
    echo "      $COMPOSE_CMD -f $COMPOSE_FILE up airflow-init"
    echo "      $COMPOSE_CMD -f $COMPOSE_FILE up -d"
    echo "      $COMPOSE_CMD -f $COMPOSE_FILE exec app python -m scripts.run_pipeline --seed-reference --date 2017-05-10"
    echo "      $COMPOSE_CMD -f $COMPOSE_FILE exec app pytest tests/unit tests/integration -q"
    echo "      Ver docs/runbooks/validacao_docker.md para o passo a passo completo."
else
    aviso "Daemon Docker não está acessível neste ambiente — build/up real não foi (e não pode ser) validado por este script"
fi

echo ""
echo "=== Resumo ==="
echo "  Passos OK: $PASSOS_OK"
echo "  Passos com falha: $PASSOS_FALHOS"

if [ "$PASSOS_FALHOS" -gt 0 ]; then
    echo ""
    echo "Corrija os itens marcados com ❌ antes de rodar 'docker compose up'."
    exit 1
fi

echo ""
echo "Validação estática concluída sem falhas. Prossiga com o build real quando"
echo "o daemon Docker estiver disponível."
