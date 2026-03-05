#!/bin/bash
# =============================================================================
# Vigilant Log Server — Setup Script
# OS: Rocky Linux 10 (instalação mínima, sem nada pré-configurado)
# Stack: rsyslog (receptor TCP 514) + Promtail + Loki + Grafana + nginx (HTTPS)
#
# Pré-requisito: Rocky Linux 10 com acesso root e internet.
# Uso: bash setup-log-server.sh
# =============================================================================

set -euo pipefail
export LANG=C.UTF-8

# Versões dos componentes (não alterar)
LOKI_VERSION="3.3.2"
PROMTAIL_VERSION="3.3.2"
TIMEZONE="America/Sao_Paulo"

# =============================================================================
LOG_DIR="/var/log/vigilant"
LOKI_DIR="/var/lib/loki"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
info() { echo -e "${YELLOW}[INFO]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step() { echo ""; echo -e "${GREEN}>>> $*${NC}"; echo ""; }

[[ $EUID -ne 0 ]] && err "Execute como root: sudo bash $0"

collect_inputs() {
    echo ""
    echo "=================================================="
    echo "   Vigilant Log Server — Configuracao inicial"
    echo "=================================================="
    echo ""

    # Hostname
    read -rp "Hostname do servidor [vigilant-logs]: " SERVER_HOSTNAME </dev/tty
    SERVER_HOSTNAME="${SERVER_HOSTNAME:-vigilant-logs}"

    # Senha do Grafana
    while true; do
        read -rsp "Senha admin do Grafana: " GRAFANA_ADMIN_PASSWORD </dev/tty; echo
        [[ -z "$GRAFANA_ADMIN_PASSWORD" ]] && { echo "Senha nao pode ser vazia."; continue; }
        read -rsp "Confirme a senha: " _pass2 </dev/tty; echo
        [[ "$GRAFANA_ADMIN_PASSWORD" == "$_pass2" ]] && break
        echo "Senhas nao conferem. Tente novamente."
    done

    # Resumo
    echo ""
    echo "--------------------------------------------------"
    echo "  Resumo da instalacao"
    echo "--------------------------------------------------"
    echo "  Hostname  : ${SERVER_HOSTNAME}"
    echo "  Timezone  : ${TIMEZONE}"
    echo "  Loki      : v${LOKI_VERSION}"
    echo "  Promtail  : v${PROMTAIL_VERSION}"
    echo "  Grafana   : admin / ****"
    echo "  Porta 514 : aberta para qualquer origem"
    echo "--------------------------------------------------"
    echo ""

    read -rp "Iniciar instalacao? [s/N]: " _confirm </dev/tty
    [[ "${_confirm,,}" =~ ^(s|sim|y|yes)$ ]] || { echo "Instalacao cancelada."; exit 0; }

    export SERVER_HOSTNAME GRAFANA_ADMIN_PASSWORD
}

collect_inputs

echo ""
echo "=================================================="
echo "   Vigilant Log Server — Iniciando instalacao"
echo "=================================================="
echo ""

# =============================================================================
# FASE 0: Preparação base do sistema operacional
# =============================================================================
step "FASE 0: Preparação base do SO"

# Hostname
hostnamectl set-hostname "$SERVER_HOSTNAME"
ok "Hostname: ${SERVER_HOSTNAME}"

# Timezone
timedatectl set-timezone "$TIMEZONE"
ok "Timezone: ${TIMEZONE}"

# NTP (chrony — vem pré-instalado no Rocky Linux mínimo)
systemctl enable --now chronyd 2>/dev/null || true
ok "NTP (chrony) ativo"

# Atualizar o sistema completamente
info "Atualizando sistema (pode demorar alguns minutos)..."
dnf upgrade -y --quiet
ok "Sistema atualizado"

# EPEL (repositório extra com pacotes adicionais)
dnf install -y epel-release --quiet
dnf install -y \
    rsyslog \
    nginx \
    curl \
    wget \
    tar \
    unzip \
    jq \
    logrotate \
    firewalld \
    openssl \
    --quiet
ok "Pacotes base instalados"

# Habilitar e iniciar firewalld (pode estar parado em instalação mínima)
systemctl enable --now firewalld
ok "firewalld iniciado"

# =============================================================================
# FASE 1: rsyslog — receptor de logs dos sensores (TCP 514)
# =============================================================================
step "FASE 1: rsyslog — receptor de logs"

mkdir -p "$LOG_DIR"
chmod 750 "$LOG_DIR"

# Criar arquivo de log com permissões corretas para Promtail ler desde o início
touch "${LOG_DIR}/sensor-updates.log"
chmod 640 "${LOG_DIR}/sensor-updates.log"

cat > /etc/rsyslog.d/40-vigilant-sensors.conf << 'EOF'
module(load="imtcp")
input(type="imtcp" port="514")

$template VigilantFormat,"%TIMESTAMP:::date-rfc3339% %HOSTNAME% %syslogtag%%msg%\n"

if $programname == 'vigilant-updater' then {
    action(
        type="omfile"
        file="/var/log/vigilant/sensor-updates.log"
        template="VigilantFormat"
        flushOnTXEnd="on"
    )
    stop
}
EOF

# SELinux: permitir rsyslog ouvir na porta 514 TCP (padrão, mas garantir)
if command -v semanage &>/dev/null; then
    semanage port -a -t syslogd_port_t -p tcp 514 2>/dev/null || \
    semanage port -m -t syslogd_port_t -p tcp 514 2>/dev/null || true
fi

systemctl enable rsyslog
systemctl restart rsyslog
ok "rsyslog configurado — ouvindo TCP 514"

# =============================================================================
# FASE 2: Loki — armazenamento de logs
# =============================================================================
step "FASE 2: Loki v${LOKI_VERSION}"

LOKI_ARCH="amd64"
LOKI_URL="https://github.com/grafana/loki/releases/download/v${LOKI_VERSION}/loki-linux-${LOKI_ARCH}.zip"

mkdir -p /etc/loki "${LOKI_DIR}"/{chunks,index,index_cache,compactor}

info "Baixando Loki..."
curl -sL "$LOKI_URL" -o /tmp/loki.zip
unzip -oq /tmp/loki.zip loki-linux-${LOKI_ARCH} -d /tmp/loki-extract 2>/dev/null || \
    unzip -oq /tmp/loki.zip -d /tmp/loki-extract
find /tmp/loki-extract -name "loki-linux-${LOKI_ARCH}" -exec install -m 755 {} /usr/local/bin/loki \;
rm -rf /tmp/loki.zip /tmp/loki-extract
ok "Loki instalado em /usr/local/bin/loki"

cat > /etc/loki/loki-config.yaml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

common:
  instance_addr: 127.0.0.1
  path_prefix: /var/lib/loki
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/index
    cache_location: /var/lib/loki/index_cache
  filesystem:
    directory: /var/lib/loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 720h
  max_query_series: 5000
  retention_period: 2160h
  unordered_writes: true

compactor:
  working_directory: /var/lib/loki/compactor
  retention_enabled: true
  retention_delete_delay: 2h
  delete_request_store: filesystem

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100
EOF

id loki &>/dev/null || useradd -r -s /sbin/nologin -d "$LOKI_DIR" loki
chown -R loki:loki "$LOKI_DIR" /etc/loki

# SELinux: permitir Loki executar e escrever
if command -v chcon &>/dev/null; then
    chcon -t bin_t /usr/local/bin/loki 2>/dev/null || true
fi

cat > /etc/systemd/system/loki.service << 'EOF'
[Unit]
Description=Loki Log Aggregation
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/loki-config.yaml
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now loki
sleep 4

systemctl is-active --quiet loki && ok "Loki rodando em :3100" || \
    err "Loki falhou. Verifique: journalctl -u loki -n 30"

# =============================================================================
# FASE 3: Promtail — lê arquivo de log e envia ao Loki
# =============================================================================
step "FASE 3: Promtail v${PROMTAIL_VERSION}"

PROMTAIL_URL="https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-${LOKI_ARCH}.zip"

info "Baixando Promtail..."
curl -sL "$PROMTAIL_URL" -o /tmp/promtail.zip
unzip -oq /tmp/promtail.zip promtail-linux-${LOKI_ARCH} -d /tmp/promtail-extract 2>/dev/null || \
    unzip -oq /tmp/promtail.zip -d /tmp/promtail-extract
find /tmp/promtail-extract -name "promtail-linux-${LOKI_ARCH}" -exec install -m 755 {} /usr/local/bin/promtail \;
rm -rf /tmp/promtail.zip /tmp/promtail-extract
ok "Promtail instalado em /usr/local/bin/promtail"

mkdir -p /etc/promtail /var/lib/promtail
cat > /etc/promtail/promtail-config.yaml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: vigilant-sensor-updates
    static_configs:
      - targets:
          - localhost
        labels:
          job: vigilant-updater
          __path__: /var/log/vigilant/sensor-updates.log

    pipeline_stages:
      - regex:
          expression: '^(?P<log_time>\S+)\s+(?P<sensor_host>\S+)\s+vigilant-updater(?:\[\d+\])?:\s*event=(?P<event>\S+)\s+sensor=(?P<sensor>\S+)\s+client=(?P<client>\S+)\s+hostname=(?P<hostname>\S+)\s+v_from=(?P<version_from>\S+)\s+v_to=(?P<version_to>\S+)\s+rollback=(?P<rollback>\S+)\s+details=(?P<details>.*)$'
      - labels:
          event:
          sensor:
          client:
          hostname:
          version_from:
          version_to:
          rollback:
      - timestamp:
          source: log_time
          format: RFC3339
EOF

id promtail &>/dev/null || useradd -r -s /sbin/nologin -d /var/lib/promtail promtail
# Promtail precisa ler /var/log/vigilant
chown promtail:promtail /var/lib/promtail /etc/promtail
chmod 750 "$LOG_DIR"
chown root:promtail "$LOG_DIR"
chown root:promtail "${LOG_DIR}/sensor-updates.log"

if command -v chcon &>/dev/null; then
    chcon -t bin_t /usr/local/bin/promtail 2>/dev/null || true
fi

cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail Log Forwarder
After=network-online.target loki.service
Wants=loki.service

[Service]
Type=simple
User=promtail
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/promtail-config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now promtail
sleep 3

systemctl is-active --quiet promtail && ok "Promtail rodando — monitorando ${LOG_DIR}/sensor-updates.log" || \
    err "Promtail falhou. Verifique: journalctl -u promtail -n 30"

# =============================================================================
# FASE 4: Grafana
# =============================================================================
step "FASE 4: Grafana"

cat > /etc/yum.repos.d/grafana.repo << 'EOF'
[grafana]
name=Grafana OSS
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
exclude=*beta*
EOF

dnf install -y grafana --quiet
ok "Grafana instalado"

# Datasource Loki (auto-provisionado)
mkdir -p /etc/grafana/provisioning/{datasources,dashboards}
cat > /etc/grafana/provisioning/datasources/vigilant-loki.yaml << 'EOF'
apiVersion: 1

datasources:
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://localhost:3100
    isDefault: true
    editable: false
    jsonData:
      maxLines: 5000
EOF

cat > /etc/grafana/provisioning/dashboards/grafana-dashboard.json << 'EOF'
{
  "title": "Vigilant Sensor Updates",
  "uid": "vigilant-updates",
  "version": 2,
  "schemaVersion": 38,
  "refresh": "30s",
  "time": { "from": "now-24h", "to": "now" },
  "timezone": "browser",
  "tags": ["vigilant", "sensors"],
  "templating": {
    "list": [
      {
        "name": "client",
        "label": "Cliente",
        "type": "query",
        "datasource": { "type": "loki", "uid": "loki" },
        "query": "label_values({job=\"vigilant-updater\"}, client)",
        "multi": true,
        "includeAll": true,
        "current": { "text": "All", "value": "$__all" }
      },
      {
        "name": "sensor",
        "label": "Sensor",
        "type": "query",
        "datasource": { "type": "loki", "uid": "loki" },
        "query": "label_values({job=\"vigilant-updater\", client=~\"$client\"}, sensor)",
        "multi": true,
        "includeAll": true,
        "current": { "text": "All", "value": "$__all" }
      },
      {
        "name": "event",
        "label": "Evento",
        "type": "query",
        "datasource": { "type": "loki", "uid": "loki" },
        "query": "label_values({job=\"vigilant-updater\"}, event)",
        "multi": true,
        "includeAll": true,
        "current": { "text": "All", "value": "$__all" }
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "title": "Total de Updates (periodo)",
      "type": "stat",
      "gridPos": { "x": 0, "y": 0, "w": 4, "h": 4 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum(count_over_time({job=\"vigilant-updater\", client=~\"$client\", event=\"update_success\"}[$__range]))",
          "legendFormat": "Updates OK"
        }
      ],
      "options": { "colorMode": "background", "graphMode": "none", "textMode": "auto" },
      "fieldConfig": { "defaults": { "color": { "mode": "fixed", "fixedColor": "green" }, "unit": "short" } }
    },
    {
      "id": 2,
      "title": "Rollbacks (periodo)",
      "type": "stat",
      "gridPos": { "x": 4, "y": 0, "w": 4, "h": 4 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum(count_over_time({job=\"vigilant-updater\", client=~\"$client\", event=\"rollback\"}[$__range]))",
          "legendFormat": "Rollbacks"
        }
      ],
      "options": { "colorMode": "background", "graphMode": "none", "textMode": "auto" },
      "fieldConfig": { "defaults": { "color": { "mode": "fixed", "fixedColor": "red" }, "unit": "short" } }
    },
    {
      "id": 3,
      "title": "Falhas de Verificacao (periodo)",
      "type": "stat",
      "gridPos": { "x": 8, "y": 0, "w": 4, "h": 4 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum(count_over_time({job=\"vigilant-updater\", client=~\"$client\", event=\"verify_failed\"}[$__range]))",
          "legendFormat": "Verify Failed"
        }
      ],
      "options": { "colorMode": "background", "graphMode": "none", "textMode": "auto" },
      "fieldConfig": { "defaults": { "color": { "mode": "fixed", "fixedColor": "orange" }, "unit": "short" } }
    },
    {
      "id": 4,
      "title": "Sensores Ativos (com log no periodo)",
      "type": "stat",
      "gridPos": { "x": 12, "y": 0, "w": 4, "h": 4 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "count(count by (sensor) (count_over_time({job=\"vigilant-updater\", client=~\"$client\"}[$__range])))",
          "legendFormat": "Sensores"
        }
      ],
      "options": { "colorMode": "background", "graphMode": "none", "textMode": "auto" },
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "thresholds" },
          "unit": "short",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": null },
              { "color": "orange", "value": 1 },
              { "color": "green", "value": 3 }
            ]
          }
        }
      }
    },
    {
      "id": 5,
      "title": "Sensores sem Atividade (24h)",
      "type": "stat",
      "gridPos": { "x": 16, "y": 0, "w": 4, "h": 4 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "count(count by (sensor) (count_over_time({job=\"vigilant-updater\", client=~\"$client\"}[$__range]))) - count(count by (sensor) (count_over_time({job=\"vigilant-updater\", client=~\"$client\"}[24h])))",
          "legendFormat": "Ausentes"
        }
      ],
      "options": { "colorMode": "background", "graphMode": "none", "textMode": "auto" },
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "thresholds" },
          "unit": "short",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null },
              { "color": "orange", "value": 1 },
              { "color": "red", "value": 2 }
            ]
          }
        }
      }
    },
    {
      "id": 10,
      "title": "Log de Eventos — Tempo Real",
      "type": "logs",
      "gridPos": { "x": 0, "y": 4, "w": 24, "h": 14 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "{job=\"vigilant-updater\", client=~\"$client\", sensor=~\"$sensor\", event=~\"$event\"}",
          "legendFormat": ""
        }
      ],
      "options": {
        "showTime": true,
        "showLabels": true,
        "showCommonLabels": false,
        "wrapLogMessage": true,
        "prettifyLogMessage": false,
        "enableLogDetails": true,
        "sortOrder": "Descending"
      }
    },
    {
      "id": 20,
      "title": "Eventos por Sensor",
      "type": "barchart",
      "gridPos": { "x": 0, "y": 18, "w": 12, "h": 8 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum by (client, sensor, event) (count_over_time({job=\"vigilant-updater\", client=~\"$client\", sensor=~\"$sensor\"}[$__range]))",
          "legendFormat": "{{client}} / {{sensor}} — {{event}}"
        }
      ]
    },
    {
      "id": 21,
      "title": "Timeline de Updates",
      "type": "timeseries",
      "gridPos": { "x": 12, "y": 18, "w": 12, "h": 8 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum by (event) (count_over_time({job=\"vigilant-updater\", client=~\"$client\", sensor=~\"$sensor\", event=~\"update_success|rollback|verify_failed\"}[$__interval]))",
          "legendFormat": "{{event}}"
        }
      ],
      "fieldConfig": {
        "defaults": { "custom": { "drawStyle": "bars", "fillOpacity": 60 } },
        "overrides": [
          { "matcher": { "id": "byName", "options": "update_success" }, "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "green" } }] },
          { "matcher": { "id": "byName", "options": "rollback" }, "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "red" } }] },
          { "matcher": { "id": "byName", "options": "verify_failed" }, "properties": [{ "id": "color", "value": { "mode": "fixed", "fixedColor": "orange" } }] }
        ]
      }
    },
    {
      "id": 30,
      "title": "Atividade por Sensor (periodo)",
      "type": "table",
      "gridPos": { "x": 0, "y": 26, "w": 24, "h": 8 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum by (client, sensor) (count_over_time({job=\"vigilant-updater\", client=~\"$client\"}[$__range]))",
          "legendFormat": "",
          "instant": true
        }
      ],
      "transformations": [
        { "id": "labelsToFields", "options": { "mode": "columns" } },
        { "id": "organize", "options": { "excludeByName": { "Time": true }, "renameByName": { "client": "Cliente", "sensor": "Sensor" } } },
        { "id": "renameByRegex", "options": { "regex": "^Value.*$", "renamePattern": "Eventos" } }
      ],
      "options": { "sortBy": [{ "displayName": "Cliente", "desc": false }], "footer": { "show": false } }
    },
    {
      "id": 40,
      "title": "Ultimo Heartbeat por Sensor (24h)",
      "type": "table",
      "gridPos": { "x": 0, "y": 34, "w": 12, "h": 8 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum by (client, sensor) (count_over_time({job=\"vigilant-updater\", client=~\"$client\", sensor=~\"$sensor\"}[24h]))",
          "legendFormat": "",
          "instant": true
        }
      ],
      "transformations": [
        { "id": "labelsToFields", "options": { "mode": "columns" } },
        { "id": "organize", "options": { "excludeByName": { "Time": true }, "renameByName": { "client": "Cliente", "sensor": "Sensor" } } },
        { "id": "renameByRegex", "options": { "regex": "^Value.*$", "renamePattern": "Checagens (24h)" } }
      ],
      "options": { "sortBy": [{ "displayName": "Sensor", "desc": false }], "footer": { "show": false } },
      "fieldConfig": {
        "overrides": [
          {
            "matcher": { "id": "byName", "options": "Checagens (24h)" },
            "properties": [
              { "id": "custom.displayMode", "value": "color-background" },
              { "id": "thresholds", "value": { "mode": "absolute", "steps": [{ "color": "red", "value": null }, { "color": "green", "value": 1 }] } },
              { "id": "color", "value": { "mode": "thresholds" } }
            ]
          }
        ]
      }
    },
    {
      "id": 41,
      "title": "Versao Atual por Sensor",
      "type": "table",
      "gridPos": { "x": 12, "y": 34, "w": 12, "h": 8 },
      "datasource": { "type": "loki", "uid": "loki" },
      "targets": [
        {
          "expr": "sum by (client, sensor, version_to) (count_over_time({job=\"vigilant-updater\", client=~\"$client\", sensor=~\"$sensor\", event=~\"no_update|update_success\"}[30m]))",
          "legendFormat": "",
          "instant": true
        }
      ],
      "transformations": [
        { "id": "labelsToFields", "options": { "mode": "columns" } },
        { "id": "organize", "options": { "excludeByName": { "Time": true }, "renameByName": { "client": "Cliente", "sensor": "Sensor", "version_to": "Versao" } } },
        { "id": "renameByRegex", "options": { "regex": "^Value.*$", "renamePattern": "Checagens (30m)" } }
      ],
      "options": { "sortBy": [{ "displayName": "Sensor", "desc": false }], "footer": { "show": false } }
    }
  ]
}
EOF

cat > /etc/grafana/provisioning/dashboards/vigilant.yaml << 'EOF'
apiVersion: 1
providers:
  - name: vigilant
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Desabilitar acesso anônimo e reforçar segurança
sed -i 's/^;admin_password\s*=.*/admin_password = '"${GRAFANA_ADMIN_PASSWORD}"'/' /etc/grafana/grafana.ini 2>/dev/null || true

cat >> /etc/grafana/grafana.ini << EOF

[auth.anonymous]
enabled = false

[security]
admin_password = ${GRAFANA_ADMIN_PASSWORD}
cookie_secure = true
cookie_samesite = strict
EOF

# SELinux: Grafana escrever seus dados
if command -v chcon &>/dev/null; then
    chcon -R -t var_t /var/lib/grafana 2>/dev/null || true
fi

systemctl enable --now grafana-server
sleep 5

systemctl is-active --quiet grafana-server && ok "Grafana rodando em :3000" || \
    err "Grafana falhou. Verifique: journalctl -u grafana-server -n 30"

# Definir senha admin via CLI (garante mesmo se grafana.ini não pegou)
grafana-cli admin reset-admin-password "$GRAFANA_ADMIN_PASSWORD" 2>/dev/null || true

# =============================================================================
# FASE 5: nginx — proxy reverso com HTTPS (certificado auto-assinado)
# =============================================================================
step "FASE 5: nginx + HTTPS"

mkdir -p /etc/nginx/ssl

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/vigilant.key \
    -out    /etc/nginx/ssl/vigilant.crt \
    -subj "/C=BR/ST=SP/O=Vigilant/CN=${SERVER_HOSTNAME}" \
    2>/dev/null
chmod 600 /etc/nginx/ssl/vigilant.key
ok "Certificado auto-assinado gerado (10 anos)"

# Remover config default do nginx
rm -f /etc/nginx/conf.d/default.conf

cat > /etc/nginx/conf.d/vigilant-logs.conf << 'EOF'
server {
    listen 80;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;

    ssl_certificate     /etc/nginx/ssl/vigilant.crt;
    ssl_certificate_key /etc/nginx/ssl/vigilant.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
EOF

# SELinux: nginx se conectar ao Grafana localmente
setsebool -P httpd_can_network_connect 1 2>/dev/null || true

# Testar config nginx antes de iniciar
nginx -t 2>/dev/null && ok "Configuração nginx válida" || err "Erro na configuração do nginx"

systemctl enable --now nginx
ok "nginx rodando — HTTPS na porta 443"

# =============================================================================
# FASE 6: Firewall
# =============================================================================
step "FASE 6: Firewall"

# HTTP e HTTPS para acesso ao Grafana (de qualquer IP)
firewall-cmd --permanent --add-service=https --quiet
firewall-cmd --permanent --add-service=http  --quiet
ok "Porta 443/80 aberta (Grafana)"

# Porta 514 TCP — para recebimento de logs dos sensores
firewall-cmd --permanent --add-port=514/tcp
ok "Porta 514/tcp aberta para qualquer origem"

firewall-cmd --reload
ok "Firewall aplicado"

# =============================================================================
# FASE 7: logrotate
# =============================================================================
step "FASE 7: logrotate"

cat > /etc/logrotate.d/vigilant-sensors << 'EOF'
/var/log/vigilant/sensor-updates.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root promtail
    sharedscripts
    postrotate
        /usr/bin/systemctl kill -s HUP rsyslog.service 2>/dev/null || true
    endscript
}
EOF
ok "logrotate configurado (90 dias)"

# =============================================================================
# RESUMO FINAL
# =============================================================================
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=================================================="
echo "   Vigilant Log Server — Instalacao concluida!"
echo "=================================================="
echo ""
echo "  Grafana:  https://${SERVER_IP}"
echo "  Login:    admin"
echo "  Senha:    ${GRAFANA_ADMIN_PASSWORD}"
echo ""
echo "  Logs:     ${LOG_DIR}/sensor-updates.log"
echo "  rsyslog:  TCP 514 — aguardando sensores"
echo ""
echo "  Proximos passos:"
echo "  1. Nos sensores, editar /etc/rsyslog.d/50-vigilant-updater.conf"
echo "     e substituir o IP pelo IP deste servidor: ${SERVER_IP}"
echo "  2. Nos sensores: systemctl restart rsyslog"
echo "  3. Testar: logger -p local0.info -t vigilant-updater 'event=test'"
echo "  4. Verificar chegada: tail -f ${LOG_DIR}/sensor-updates.log"
echo ""
echo "  Status dos servicos:"
for svc in rsyslog loki promtail grafana-server nginx; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null)
    if [[ "$STATUS" == "active" ]]; then
        echo "    [OK]  $svc"
    else
        echo "    [!!]  $svc — VERIFICAR"
    fi
done
echo ""
echo "=================================================="
