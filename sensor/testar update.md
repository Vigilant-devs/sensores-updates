# Procedimento para Atualizar os Sensores:

Adicionar ou editar os arquivos nos seus respectivos diretorios:
vim check.sh

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

# Registrar a execucao e o agendamento no custom-deploy.sh 
# Edit custom-deploy.sh

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


# Passo 3 - Commitar e publicar como v2.0.2 
cd /Users/senna/WORK/Sensores-Updates
git add sensor/configs/bettercap/check.sh sensor/custom-deploy.sh
git commit -m "feat: adicionar check.sh bettercap com cron 13:20 diario"
git tag v2.0.2
git push origin main && git push origin v2.0.2



# Passo 4 — Aguardar CI e monitorar
# Após o push o CI (~2 min) empacota e cria o release. 
# Depois monitore no servidor:
tail -f /var/log/vigilant/sensor-updates.log | grep -E "update_started|update_success"

Quando cada sensor aplicar o update, o check.sh vai:

Ser copiado para /etc/bettercap/check.sh
Ser executado imediatamente
Criar o cron em /etc/cron.d/vigilant-bettercap-check (roda todo dia 13:20)

# Agora monitore o update nos sensores:
tail -f /var/log/vigilant/sensor-updates.log | grep -E "update_started|update_success|update_failed"

Os sensores vão detectar a v2.0.2 no próximo ciclo de 5 minutos e aplicar. Ao final de cada update você verá:

event=update_started v_from=2.0.1 v_to=2.0.2
event=update_success v_from=2.0.1 v_to=2.0.2

E no sensor, o check.sh será executado imediatamente e o cron criado em /etc/cron.d/vigilant-bettercap-check.


# Perfeito. Todos os 4 sensores atualizados para v2.0.2 com sucesso:

Sensor	Início	Conclusão	Status
sensor-04	13:12:17	13:13:04	✓
sensor-1	13:13:16	13:14:02	✓
sensor-2	13:13:22	13:14:08	✓
sensor-3	13:13:27	13:14:14	✓

O check.sh foi copiado para /etc/bettercap/check.sh, executado uma vez e o cron agendado para 13:20 diário em cada sensor.

Verifique em um sensor se o cron foi criado corretamente:


ssh -p 12222 root@172.16.162.197 "cat /etc/cron.d/vigilant-bettercap-check && cat /var/log/vigilant/bettercap-check.log"




# Ajustar melhorias no Grafana

Melhorias aplicadas no Grafana Dashboard
Correções de bugs
Problema	Fix
"Sensores Ativos" usava [24h] fixo	→ [$__range] (respeita o filtro de tempo do painel)
Variável $event: label_values(event) sem filtro	→ label_values({job="vigilant-updater"}, event)
"Sensores por Cliente" só mostrava sensores com update_success	→ mostra todos com qualquer evento no [$__range]
Tempo padrão era now-7d	→ now-24h
Novos painéis adicionados
Painel	Descrição
Sensores sem Atividade (24h)	Stat panel com cor vermelha quando ≥2 sensores ausentes — alerta visual imediato
Último Heartbeat por Sensor	Tabela com contagem de eventos nas últimas 24h — célula verde se ativo, vermelha se ausente
Versão Atual por Sensor	Tabela com version_to baseado nos últimos 6h de no_update ou update_success
Melhoria visual
"Sensores Ativos": cor agora usa thresholds (vermelho=0, laranja=1-2, verde=3+) em vez de verde fixo


Para importar no Grafana:

# Copiar o JSON para o servidor
scp server/grafana-dashboard.json root@172.16.162.189:/tmp/

# No servidor — importar via API
curl -s -u admin:Vigilant2026!@#$% \
  -H "Content-Type: application/json" \
  -d "{\"dashboard\": $(cat /tmp/grafana-dashboard.json), \"overwrite\": true, \"folderId\": 0}" \
  http://localhost:3000/api/dashboards/import



PASS='Vigilant2026!@#$%'
jq -n --slurpfile dash /tmp/grafana-dashboard.json \
  '{"dashboard": $dash[0], "overwrite": true, "folderId": 0}' | \
curl -s -u "admin:${PASS}" \
  -H "Content-Type: application/json" \
  -d @- \
  http://localhost:3000/api/dashboards/import







O Grafana não deixa sobrescrever dashboards que foram provisionados por arquivo. Precisamos atualizar o arquivo diretamente no disco e recarregar o provisionamento:


# Verificar onde está o arquivo provisionado
find /etc/grafana/provisioning /var/lib/grafana -name "*.json" 2>/dev/null | grep -i vigilant
Se encontrar o arquivo, substitua e recarregue:


# Copiar para o local correto (ajuste o path se necessário)
cp /tmp/grafana-dashboard.json /etc/grafana/provisioning/dashboards/grafana-dashboard.json

# Recarregar provisioning via API (sem reiniciar o serviço)
PASS='Vigilant2026!@#$%'
curl -s -u "admin:${PASS}" -X POST \
  http://localhost:3000/api/admin/provisioning/dashboards/reload
Ou se preferir importar como dashboard novo (sem conflito de uid), remova o uid antes:


PASS='Vigilant2026!@#$%'
jq -n --slurpfile dash /tmp/grafana-dashboard.json \
  '{"dashboard": ($dash[0] | del(.uid, .id, .version)), "overwrite": false, "folderId": 0}' | \
curl -s -u "admin:${PASS}" \
  -H "Content-Type: application/json" \
  -d @- \
  http://localhost:3000/api/dashboards/import
Qual o output do find?