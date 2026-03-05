#!/bin/bash
# =============================================================================
# check.sh — Vigilant Sensor / Bettercap Health Check
# Agendado via cron: todo dia 13:20
# =============================================================================

LOGFILE="/var/log/vigilant/bettercap-check.log"
mkdir -p "$(dirname "$LOGFILE")"

log() { echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*" | tee -a "$LOGFILE"; }

log "=== Bettercap check iniciado ==="

# Verificar se o serviço bettercap está ativo
if systemctl is-active --quiet bettercap; then
    log "bettercap: OK (running)"
else
    log "bettercap: WARN (not running) — tentando reiniciar..."
    systemctl start bettercap 2>/dev/null && log "bettercap: reiniciado OK" || log "bettercap: falha ao reiniciar"
fi

log "=== Bettercap check concluído ==="
