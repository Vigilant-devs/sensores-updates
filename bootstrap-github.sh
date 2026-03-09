#!/bin/bash
# =============================================================================
# Vigilant Sensor — Bootstrap GitHub
# Automatiza: MANIFEST_URL + git init + gh repo create + GPG + secrets + release
#
# Uso: bash tools/bootstrap-github.sh <ORG> <REPO> [VERSAO]
# Exemplo: bash tools/bootstrap-github.sh Vigilant-devs sensores-updates 1.0.0
#
# Pré-requisitos: git, gh (autenticado), gpg
# Execute a partir da raiz do repositório local.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# ARGUMENTOS
# =============================================================================
GITHUB_ORG="${1:-}"
GITHUB_REPO="${2:-}"
FIRST_VERSION="${3:-1.0.0}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
info() { echo -e "${YELLOW}[INFO]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step() { echo ""; echo -e "${GREEN}>>> $*${NC}"; echo ""; }

if [[ -z "$GITHUB_ORG" || -z "$GITHUB_REPO" ]]; then
    echo ""
    echo "  Uso: bash tools/bootstrap-github.sh <ORG> <REPO> [VERSAO]"
    echo "  Exemplo: bash tools/bootstrap-github.sh Vigilant-devs sensores-updates 1.0.0"
    echo ""
    exit 1
fi

echo ""
echo "=========================================================="
echo "   Vigilant Sensor — Bootstrap GitHub"
echo "=========================================================="
echo ""
echo "  Org/Repo   : ${GITHUB_ORG}/${GITHUB_REPO}"
echo "  Versão      : v${FIRST_VERSION}"
echo "  Raiz local  : ${REPO_ROOT}"
echo ""

# =============================================================================
# PRÉ-REQUISITOS
# =============================================================================
step "Verificando pré-requisitos"

for cmd in git gh gpg; do
    command -v "$cmd" &>/dev/null || err "'$cmd' não encontrado. Instale e tente novamente."
    ok "$cmd disponível"
done

gh auth status &>/dev/null || err "Não autenticado no GitHub CLI. Execute: gh auth login"
ok "GitHub CLI autenticado"

# =============================================================================
# FASE 1: MANIFEST_URL no updater
# =============================================================================
step "FASE 1: Atualizando MANIFEST_URL no updater"

MANIFEST_URL="https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/main/manifest.json"
UPDATER_FILE="${REPO_ROOT}/updater/vigilant-updater.sh"

[[ -f "$UPDATER_FILE" ]] || err "Arquivo não encontrado: ${UPDATER_FILE}"

CURRENT_URL=$(grep "^MANIFEST_URL=" "$UPDATER_FILE" | head -1 | cut -d'"' -f2)
if [[ "$CURRENT_URL" != "$MANIFEST_URL" ]]; then
    sed -i.bak "s|^MANIFEST_URL=.*|MANIFEST_URL=\"${MANIFEST_URL}\"|" "$UPDATER_FILE"
    rm -f "${UPDATER_FILE}.bak"
    ok "MANIFEST_URL atualizado → ${MANIFEST_URL}"
else
    ok "MANIFEST_URL já correto"
fi

# =============================================================================
# FASE 2: Git local
# =============================================================================
step "FASE 2: Repositório git local"

cd "$REPO_ROOT"

if [[ ! -d ".git" ]]; then
    git init
    git branch -M main
    ok "Git inicializado (branch: main)"
else
    ok "Git já inicializado"
fi

# =============================================================================
# FASE 3: GitHub — criar repositório e configurar remote
# =============================================================================
step "FASE 3: Repositório GitHub"

if gh repo view "${GITHUB_ORG}/${GITHUB_REPO}" &>/dev/null; then
    info "Repositório já existe: github.com/${GITHUB_ORG}/${GITHUB_REPO}"
else
    gh repo create "${GITHUB_ORG}/${GITHUB_REPO}" \
        --public \
        --description "Vigilant Sensor Remote Updater"
    ok "Repositório criado: github.com/${GITHUB_ORG}/${GITHUB_REPO}"
fi

REMOTE_URL="https://github.com/${GITHUB_ORG}/${GITHUB_REPO}.git"
if git remote get-url origin &>/dev/null; then
    git remote set-url origin "$REMOTE_URL"
    ok "Remote 'origin' atualizado: ${REMOTE_URL}"
else
    git remote add origin "$REMOTE_URL"
    ok "Remote 'origin' adicionado: ${REMOTE_URL}"
fi

# =============================================================================
# FASE 4: Chave GPG
# =============================================================================
step "FASE 4: Chave GPG"

GPG_EMAIL="updater@vigilant.com.br"
PRIVATE_KEY_FILE="${SCRIPT_DIR}/vigilant-private.key.asc"
PUBLIC_KEY_FILE="${REPO_ROOT}/updater/vigilant.pub.gpg"

EXISTING=$(gpg --list-secret-keys "$GPG_EMAIL" 2>/dev/null | grep -c "sec" || true)

if [[ "$EXISTING" -gt 0 ]]; then
    info "Chave GPG já existe para ${GPG_EMAIL} — reutilizando"
else
    info "Gerando chave RSA 4096 (sem passphrase)..."
    gpg --batch --gen-key <<EOF
%no-protection
Key-Type: RSA
Key-Length: 4096
Key-Usage: sign
Name-Real: Vigilant Sensor Updater
Name-Email: ${GPG_EMAIL}
Expire-Date: 2y
%commit
EOF
    ok "Chave GPG gerada"
fi

FINGERPRINT=$(gpg --list-keys --with-colons "$GPG_EMAIL" 2>/dev/null \
    | awk -F: '/^fpr/{print $10; exit}')
ok "Fingerprint: ${FINGERPRINT}"

# Exportar chave pública para o repo
mkdir -p "$(dirname "$PUBLIC_KEY_FILE")"
gpg --armor --export "$GPG_EMAIL" > "$PUBLIC_KEY_FILE"
ok "Chave pública exportada: updater/vigilant.pub.gpg"

# Exportar chave privada (para GitHub Secrets)
if [[ ! -f "$PRIVATE_KEY_FILE" ]]; then
    gpg --armor --export-secret-keys "$GPG_EMAIL" > "$PRIVATE_KEY_FILE"
    chmod 600 "$PRIVATE_KEY_FILE"
    ok "Chave privada exportada: tools/vigilant-private.key.asc (chmod 600)"
else
    info "Chave privada já existe: ${PRIVATE_KEY_FILE}"
fi

# =============================================================================
# FASE 5: Commit inicial e push
# =============================================================================
step "FASE 5: Commit e push inicial"

git add -A

if git diff --staged --quiet; then
    info "Nada para commitar — working tree limpo"
else
    git commit -m "chore: initial repository setup"
    ok "Commit inicial criado"
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
git push -u origin "${CURRENT_BRANCH}" 2>/dev/null || git push origin "${CURRENT_BRANCH}"
ok "Push → origin/${CURRENT_BRANCH}"

# =============================================================================
# FASE 6: GitHub Secrets
# =============================================================================
step "FASE 6: GitHub Secrets"

gh secret set GPG_PRIVATE_KEY \
    --repo "${GITHUB_ORG}/${GITHUB_REPO}" \
    < "$PRIVATE_KEY_FILE"
ok "Secret GPG_PRIVATE_KEY configurado"

gh secret set GPG_PASSPHRASE \
    --repo "${GITHUB_ORG}/${GITHUB_REPO}" \
    --body ""
ok "Secret GPG_PASSPHRASE configurado (vazio — chave sem passphrase)"

# =============================================================================
# FASE 7: Primeiro release
# =============================================================================
step "FASE 7: Publicando release v${FIRST_VERSION}"

TAG="v${FIRST_VERSION}"

if git tag -l "$TAG" | grep -q "^${TAG}$"; then
    info "Tag ${TAG} já existe — pulando"
else
    git tag "$TAG"
    git push origin "$TAG"
    ok "Tag ${TAG} publicada — GitHub Actions iniciado"

    echo ""
    info "Aguardando CI/CD... (pode levar 1-2 minutos)"
    sleep 15
    gh run watch --repo "${GITHUB_ORG}/${GITHUB_REPO}" || \
        info "CI em andamento — acompanhe em: gh run list --repo ${GITHUB_ORG}/${GITHUB_REPO}"
fi

# Pull do manifest.json atualizado pelo CI
git pull origin "${CURRENT_BRANCH}" --quiet 2>/dev/null || true

# =============================================================================
# RESUMO
# =============================================================================
echo ""
echo "=========================================================="
echo "   Bootstrap concluído!"
echo "=========================================================="
echo ""
echo "  Repositório : https://github.com/${GITHUB_ORG}/${GITHUB_REPO}"
echo "  Release     : ${TAG}"
echo "  Fingerprint : ${FINGERPRINT}"
echo ""
echo "  ARQUIVOS GERADOS:"
echo "  - updater/vigilant.pub.gpg       ← commitar no repo (seguro)"
echo "  - tools/vigilant-private.key.asc ← NUNCA commitar (gitignored)"
echo ""
echo "  PRÓXIMOS PASSOS:"
echo "  1. Setup servidor de logs: bash server/setup-log-server.sh"
echo "  2. Instalar updater nos sensores"
echo "  3. Verificar Grafana"
echo ""
echo "  Manifest atual:"
cat "${REPO_ROOT}/manifest.json" 2>/dev/null || true
echo ""
echo "=========================================================="
