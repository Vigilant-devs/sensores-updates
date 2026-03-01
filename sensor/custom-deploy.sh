#!/bin/bash
# =============================================================================
# Vigilant Sensor — Custom Deploy Hook
# Executado pelo post-install.sh para logica de deploy nao padrao.
# =============================================================================

set -euo pipefail

RELEASE_DIR="${1:-}"

# Atualizar config do rsyslog se incluida no pacote
RSYSLOG_SRC="${RELEASE_DIR}/rsyslog-sensor.conf"
RSYSLOG_DST="/etc/rsyslog.d/50-vigilant-updater.conf"
LOG_SERVER_IP_FILE="/vigilant/scripts/log_server_ip"

if [[ -f "$RSYSLOG_SRC" ]]; then
    if [[ -f "$LOG_SERVER_IP_FILE" ]]; then
        LOG_SERVER_IP=$(cat "$LOG_SERVER_IP_FILE")
        sed "s/__LOG_SERVER_IP__/${LOG_SERVER_IP}/g" "$RSYSLOG_SRC" > "$RSYSLOG_DST"
        echo "[custom-deploy] rsyslog config atualizado com IP: ${LOG_SERVER_IP}"
    else
        cp "$RSYSLOG_SRC" "$RSYSLOG_DST"
        echo "[custom-deploy] rsyslog config copiado (log_server_ip nao encontrado)"
    fi
    systemctl restart rsyslog 2>/dev/null || true
fi

# Instalar e executar hook pos-atualizacao
CHECK_SRC="${RELEASE_DIR}/scripts/check.sh"
CHECK_DST="/opt/check.sh"
if [[ -f "$CHECK_SRC" ]]; then
    cp "$CHECK_SRC" "$CHECK_DST"
    chmod +x "$CHECK_DST"
    echo "[custom-deploy] Hook instalado: ${CHECK_DST}"
    echo "[custom-deploy] Executando hook pos-atualizacao..."
    bash "$CHECK_DST" && echo "[custom-deploy] Hook concluido com sucesso." \
                      || echo "[custom-deploy] Hook retornou erro (ignorado)."
fi

# Auto-atualizacao do proprio script do updater
UPDATER_SRC="${RELEASE_DIR}/updater/vigilant-updater.sh"
UPDATER_DST="/vigilant/scripts/vigilantsensor/updater/vigilant-updater.sh"
if [[ -f "$UPDATER_SRC" ]]; then
    cp "$UPDATER_SRC" "$UPDATER_DST"
    chmod +x "$UPDATER_DST"
    echo "[custom-deploy] vigilant-updater.sh atualizado para versao do pacote."
fi

exit 0
