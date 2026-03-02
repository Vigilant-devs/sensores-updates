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

# Auto-atualizacao do proprio script do updater
UPDATER_SRC="${RELEASE_DIR}/updater/vigilant-updater.sh"
UPDATER_DST="/vigilant/scripts/vigilantsensor/updater/vigilant-updater.sh"
if [[ -f "$UPDATER_SRC" ]]; then
    cp "$UPDATER_SRC" "$UPDATER_DST"
    chmod +x "$UPDATER_DST"
    echo "[custom-deploy] vigilant-updater.sh atualizado para versao do pacote."
fi

# Agendar e executar check.sh do bettercap
CHECK_DST="/etc/bettercap/check.sh"
if [[ -f "$CHECK_DST" ]]; then
    chmod +x "$CHECK_DST"
    echo "[custom-deploy] check.sh: permissao de execucao aplicada"

    # Adicionar cron se ainda nao existir (todo dia 13:20)
    CRON_LINE="20 13 * * * root $CHECK_DST >> /var/log/vigilant/bettercap-check.log 2>&1"
    CRON_FILE="/etc/cron.d/vigilant-bettercap-check"
    if ! grep -qF "$CHECK_DST" "$CRON_FILE" 2>/dev/null; then
        echo "$CRON_LINE" > "$CRON_FILE"
        chmod 644 "$CRON_FILE"
        echo "[custom-deploy] cron agendado: $CRON_FILE (13:20 diario)"
    else
        echo "[custom-deploy] cron ja existe: $CRON_FILE"
    fi

    # Executar imediatamente na primeira instalacao
    echo "[custom-deploy] Executando check.sh agora..."
    bash "$CHECK_DST" && echo "[custom-deploy] check.sh OK" \
                      || echo "[custom-deploy] check.sh retornou erro (ignorado)"
fi

exit 0
