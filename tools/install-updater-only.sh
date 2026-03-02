#!/bin/bash
# =============================================================================
# Vigilant Sensor — Instalador do Updater (sensores legados)
#
# Instala SOMENTE o vigilant-updater em sensores que já estão configurados
# mas não possuem o sistema de atualização automática.
#
# NÃO altera: hostname, VPN, Snort, Dionaea, Cowrie, Bettercap, ExaBGP.
#
# Uso:
#   bash install-updater-only.sh
# =============================================================================

set -euo pipefail

[[ $EUID -ne 0 ]] && { echo "[ERROR] Execute como root."; exit 1; }

GITHUB_RAW="https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main"
UPDATER_DIR="/vigilant/scripts/vigilantsensor/updater"
LOG_DIR="/vigilant/scripts/vigilantsensor/logs"
IDENTITY_DIR="/vigilant/scripts"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
color_green() { echo -e "\033[1;32m$*\033[0m"; }
color_blue()  { echo -e "\033[1;34m$*\033[0m"; }
color_red()   { echo -e "\033[1;31m$*\033[0m"; }
color_yellow(){ echo -e "\033[1;33m$*\033[0m"; }
log()         { echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*"; }

# -----------------------------------------------------------------------------
# Coleta de inputs
# -----------------------------------------------------------------------------
echo ""
color_blue "============================================================"
color_blue "   Vigilant Updater — Instalação em Sensor Legado"
color_blue "============================================================"
echo ""

# Sensor ID
EXISTING_SENSOR_ID=""
if [[ -f "${IDENTITY_DIR}/sensor_id" ]]; then
    EXISTING_SENSOR_ID=$(cat "${IDENTITY_DIR}/sensor_id")
    echo "sensor_id existente detectado: ${EXISTING_SENSOR_ID}"
fi

while true; do
    read -rp "Enter sensor_id [ex: sensor-01]${EXISTING_SENSOR_ID:+ (Enter para manter '${EXISTING_SENSOR_ID}')}: " INPUT < /dev/tty
    [[ -z "$INPUT" && -n "$EXISTING_SENSOR_ID" ]] && INPUT="$EXISTING_SENSOR_ID"
    if [[ "$INPUT" =~ ^[a-zA-Z0-9-]+$ ]]; then
        SENSOR_ID="$INPUT"
        break
    fi
    color_red "[ERROR] Apenas letras, numeros e hifens."
done
read -rp "You answered '${SENSOR_ID}'. Continue? (Y/N): " _c < /dev/tty
[[ "${_c^^}" != "Y" ]] && { echo "Abortado."; exit 0; }

echo ""

# Client ID (Vigilant ID)
EXISTING_CLIENT_ID=""
if [[ -f "${IDENTITY_DIR}/vigilant_client_id" ]]; then
    EXISTING_CLIENT_ID=$(cat "${IDENTITY_DIR}/vigilant_client_id")
    echo "vigilant_client_id existente detectado: ${EXISTING_CLIENT_ID}"
fi

while true; do
    read -rp "Enter Vigilant ID (client_id)${EXISTING_CLIENT_ID:+ (Enter para manter '${EXISTING_CLIENT_ID}')}: " INPUT < /dev/tty
    [[ -z "$INPUT" && -n "$EXISTING_CLIENT_ID" ]] && INPUT="$EXISTING_CLIENT_ID"
    if [[ "$INPUT" =~ ^[a-zA-Z0-9-]+$ ]]; then
        CLIENT_ID="$INPUT"
        break
    fi
    color_red "[ERROR] Apenas letras, numeros e hifens."
done
read -rp "You answered '${CLIENT_ID}'. Continue? (Y/N): " _c < /dev/tty
[[ "${_c^^}" != "Y" ]] && { echo "Abortado."; exit 0; }

echo ""

# IP do servidor de logs
EXISTING_LOG_SERVER=""
if [[ -f "${IDENTITY_DIR}/log_server_ip" ]]; then
    EXISTING_LOG_SERVER=$(cat "${IDENTITY_DIR}/log_server_ip")
    echo "log_server_ip existente detectado: ${EXISTING_LOG_SERVER}"
fi

while true; do
    read -rp "Enter IP da Central Updates (Grafana/rsyslog)${EXISTING_LOG_SERVER:+ (Enter para manter '${EXISTING_LOG_SERVER}')}: " INPUT < /dev/tty
    [[ -z "$INPUT" && -n "$EXISTING_LOG_SERVER" ]] && INPUT="$EXISTING_LOG_SERVER"
    if [[ "$INPUT" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        LOG_SERVER_IP="$INPUT"
        break
    fi
    color_red "[ERROR] IP invalido. Use o formato: X.X.X.X (ex: 172.16.162.189)"
done
read -rp "You answered '${LOG_SERVER_IP}'. Continue? (Y/N): " _c < /dev/tty
[[ "${_c^^}" != "Y" ]] && { echo "Abortado."; exit 0; }

# Confirmação final
echo ""
color_blue "============================================================"
echo "  sensor_id  : ${SENSOR_ID}"
echo "  client_id  : ${CLIENT_ID}"
echo "  log_server : ${LOG_SERVER_IP}"
color_blue "============================================================"
read -rp "Confirma instalacao? (Y/N): " _final < /dev/tty
[[ "${_final^^}" != "Y" ]] && { echo "Abortado."; exit 0; }

echo ""
log "Iniciando instalacao do Vigilant Updater..."

# -----------------------------------------------------------------------------
# Dependência: jq
# -----------------------------------------------------------------------------
if ! command -v jq &>/dev/null; then
    log "Instalando jq..."
    dnf install -y jq &>/dev/null || yum install -y jq &>/dev/null || {
        color_red "[ERROR] Nao foi possivel instalar jq. Instale manualmente e tente novamente."
        exit 1
    }
    log "jq instalado."
fi

# -----------------------------------------------------------------------------
# Criar diretórios
# -----------------------------------------------------------------------------
mkdir -p "$UPDATER_DIR" "$LOG_DIR"
log "Diretorios criados: ${UPDATER_DIR}"

# -----------------------------------------------------------------------------
# Baixar arquivos do GitHub
# -----------------------------------------------------------------------------
FILES=(
    "updater/vigilant-updater.sh"
    "updater/vigilant.pub.gpg"
    "updater/vigilant-updater.service"
    "updater/vigilant-updater-test.timer"
    "updater/vigilant-updater.timer"
)

for f in "${FILES[@]}"; do
    filename=$(basename "$f")
    if curl -fsSL --max-time 30 "${GITHUB_RAW}/${f}" -o "${UPDATER_DIR}/${filename}"; then
        log "Baixado: ${filename}"
    else
        color_red "[ERROR] Falha ao baixar: ${filename}"
        exit 1
    fi
done

chmod +x "${UPDATER_DIR}/vigilant-updater.sh"

# -----------------------------------------------------------------------------
# Gravar identidade e versão
# -----------------------------------------------------------------------------
echo "$SENSOR_ID"    > "${IDENTITY_DIR}/sensor_id"
echo "$CLIENT_ID"    > "${IDENTITY_DIR}/vigilant_client_id"
echo "$LOG_SERVER_IP" > "${IDENTITY_DIR}/log_server_ip"
chmod 644 "${IDENTITY_DIR}/sensor_id" \
          "${IDENTITY_DIR}/vigilant_client_id" \
          "${IDENTITY_DIR}/log_server_ip"

# Versão inicial — o updater se auto-atualizará na primeira execução
MANIFEST_VERSION=$(curl -fsSL --max-time 15 \
    "https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/manifest.json" \
    2>/dev/null | grep '"version"' | head -1 | sed 's/.*"version": *"\([^"]*\)".*/\1/' || echo "1.0.0")
echo "$MANIFEST_VERSION" > "${UPDATER_DIR}/VERSION"
log "Versao registrada: ${MANIFEST_VERSION}"

# -----------------------------------------------------------------------------
# Instalar e ativar serviços systemd
# -----------------------------------------------------------------------------
cp "${UPDATER_DIR}/vigilant-updater.service"    /etc/systemd/system/
cp "${UPDATER_DIR}/vigilant-updater-test.timer" /etc/systemd/system/
cp "${UPDATER_DIR}/vigilant-updater.timer"      /etc/systemd/system/

systemctl daemon-reload
systemctl enable vigilant-updater-test.timer
systemctl start  vigilant-updater-test.timer
log "Timer ativado: vigilant-updater-test.timer (a cada 5 minutos)"

# -----------------------------------------------------------------------------
# Configurar rsyslog forwarding
# -----------------------------------------------------------------------------
cat > /etc/rsyslog.d/50-vigilant-updater.conf << EOF
if \$programname == 'vigilant-updater' then @@${LOG_SERVER_IP}:514
& stop
EOF

systemctl restart rsyslog
log "rsyslog configurado para enviar logs para ${LOG_SERVER_IP}:514"

# -----------------------------------------------------------------------------
# Resultado
# -----------------------------------------------------------------------------
echo ""
color_green "============================================================"
color_green "   Vigilant Updater instalado com sucesso!"
color_green "============================================================"
echo "  sensor_id  : ${SENSOR_ID}"
echo "  client_id  : ${CLIENT_ID}"
echo "  versao     : ${MANIFEST_VERSION}"
echo "  log_server : ${LOG_SERVER_IP}:514"
echo ""
echo "Proxima verificacao automatica em ate 5 minutos."
echo "Para forcar agora: systemctl start vigilant-updater.service"
echo ""
log "Para acompanhar: journalctl -u vigilant-updater.service -f"
