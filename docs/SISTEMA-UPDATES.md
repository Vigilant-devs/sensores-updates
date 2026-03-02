# Vigilant NDR — Sistema de Atualização Remota de Sensores

**Repositório:** `Vigilant-devs/sensores-updates`
**Versão do sistema:** conforme `manifest.json` na raiz do repositório
**Equipe responsável:** P&D — Vigilant Labs

---

## Visão Geral

O sistema de atualização remota permite distribuir scripts, configurações e binários para todos os sensores Vigilant NDR de forma segura, auditada e automática — sem acesso direto a cada sensor.

Cada sensor verifica periodicamente se há uma nova versão disponível no GitHub. Quando detectada, o pacote é baixado, verificado (SHA256 + assinatura GPG) e instalado atomicamente. Se o serviço de saúde falhar após a instalação, o sistema faz rollback automático para a versão anterior. Todos os eventos são reportados ao servidor de logs central via rsyslog/VPN, visíveis em tempo real no Grafana.

---

## Arquitetura

```
┌────────────────────────────────────────────────────────────────┐
│                        GITHUB (público)                        │
│                                                                │
│   manifest.json ──── versão atual, URL, SHA256, sig_url        │
│   Releases/vX.Y.Z ── sensor-pack.tar.gz                       │
│                       sensor-pack.tar.gz.sig  (GPG)           │
│                       sensor-pack.tar.gz.sha256               │
└────────────────────────┬───────────────────────────────────────┘
                         │ HTTPS (pull periódico)
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     [sensor-01]    [sensor-02]    [sensor-N]
          │              │              │
          └──────────────┴──────────────┘
                         │ rsyslog TCP / VPN
                         ▼
              ┌─────────────────────┐
              │  vigilant-logs      │
              │  172.16.162.189     │
              │                     │
              │  rsyslog → Promtail │
              │  Loki               │
              │  Grafana            │
              └─────────────────────┘
```

---

## Estrutura do Repositório

```
Sensores-Updates/
├── .github/
│   └── workflows/
│       └── release.yml          # CI/CD: empacota, assina e publica release
│
├── sensor/                      # Conteúdo do pacote distribuído aos sensores
│   ├── scripts/                 # → /vigilant/scripts/
│   ├── configs/
│   │   ├── snort/               # → /etc/snort/
│   │   ├── dionaea/             # → /etc/dionaea/
│   │   ├── cowrie/              # → /home/cowrie/cowrie/etc/
│   │   ├── bettercap/           # → /etc/bettercap/
│   │   └── exabgp/              # → /etc/exabgp/
│   ├── post-install.sh          # Copia arquivos para destinos finais no sensor
│   └── custom-deploy.sh         # Hooks de deploy não-padrão (rsyslog, crons, self-update)
│
├── updater/                     # Instalado no sensor uma única vez
│   ├── vigilant-updater.sh      # Daemon principal (todas as fases do update)
│   ├── vigilant-updater.service # Systemd service (oneshot)
│   ├── vigilant-updater.timer   # Timer produção: domingo 03h
│   ├── vigilant-updater-test.timer  # Timer teste: a cada 1h
│   ├── vigilant.pub.gpg         # Chave pública GPG para verificação dos pacotes
│   └── rsyslog-sensor.conf      # Config rsyslog do sensor → central de logs
│
├── server/                      # Configuração do servidor de logs central
│   ├── setup-log-server.sh      # Script de setup completo (Rocky Linux)
│   ├── loki-config.yaml         # Configuração do Loki
│   ├── promtail-config.yaml     # Pipeline de ingestão de logs
│   ├── grafana-dashboard.json   # Dashboard provisionado
│   ├── grafana-datasource.yaml  # Datasource Loki para o Grafana
│   └── rsyslog-server.conf      # Recebe logs dos sensores na porta 514/TCP
│
├── tools/
│   ├── generate-gpg-key.sh      # Gera par de chaves GPG (uma única vez)
│   ├── pack-release.sh          # Empacota sensor/ em sensor-pack.tar.gz
│   ├── sign-release.sh          # Assina o pacote localmente (opcional)
│   └── install-updater-only.sh  # Instala o updater em sensores legados
│
└── manifest.json                # Ponteiro da versão atual (atualizado pelo CI)
```

---

## Como Funciona — Fluxo Completo

### 1. Publicação de Nova Versão (desenvolvedor)

```
Desenvolvedor faz alterações em sensor/
         │
         ▼
git tag vX.Y.Z && git push origin vX.Y.Z
         │
         ▼
GitHub Actions (release.yml) dispara automaticamente:
  1. Empacota sensor/ → sensor-pack-vX.Y.Z.tar.gz
  2. Calcula SHA256
  3. Assina com GPG (chave privada via Secret)
  4. Cria GitHub Release com os 3 assets
  5. Atualiza manifest.json no main
```

### 2. Ciclo de Atualização no Sensor (automático)

O timer systemd dispara `vigilant-updater.service` a cada 1h (modo teste) ou domingo às 03h (produção).

```
[FASE 1] Fetch manifest
         Baixa manifest.json do GitHub (cache-bust via timestamp)
         ↓
[FASE 2] Comparação de versões (semver MAJOR.MINOR.PATCH)
         Se remote_version <= local_version → event=no_update → fim
         ↓
[FASE 3] Download do pacote
         Baixa sensor-pack.tar.gz + .sig com 3 tentativas e timeout 15s
         ↓
[FASE 4] Verificação de integridade
         SHA256: compara hash calculado vs esperado no manifest
         GPG: valida assinatura com chave pública em keyring isolado
         Qualquer falha → event=verify_failed → ABORT (pacote rejeitado)
         ↓
[FASE 5] Instalação atômica
         Extrai pacote em releases/vX.Y.Z/
         Symlink atomic: staging_link → mv -T → current
         Preserva previous como fallback de rollback
         Atualiza arquivo VERSION
         ↓
[FASE 5b] Post-install
          Executa post-install.sh do pacote
          Copia scripts → /vigilant/scripts/
          Copia configs → /etc/snort/, /etc/dionaea/, etc.
          Executa custom-deploy.sh (rsyslog, crons, self-update do updater)
         ↓
[FASE 5c] Restart de serviços
          Reinicia: snort, dionaea, cowrie-ssh, cowrie-telnet
         ↓
[FASE 6] Health check (aguarda 30s)
         Verifica se todos os serviços estão active
         ↓ (falha)
[FASE 7] Rollback automático
         Reverte symlink current → previous
         Re-executa post-install da versão anterior
         Reinicia serviços na versão anterior
         event=rollback reportado ao servidor central
         ↓ (sucesso)
event=update_success reportado ao servidor central
Limpa releases antigas (mantém apenas current + previous)
```

### 3. Reporte de Eventos

Cada fase gera um evento reportado de duas formas:

| Canal | Mecanismo | Confiabilidade |
|---|---|---|
| **Primário** | `logger` → rsyslog TCP → `172.16.162.189:514` | Alta — fila local, entrega garantida via VPN |
| **Secundário** | HTTP POST para `STATUS_URL` (opcional) | Melhor-esforço — silenciosamente ignorado se indisponível |

**Formato do log (rsyslog → Promtail → Loki):**
```
2026-03-02T15:30:00+00:00 sensor-01 vigilant-updater[PID]: event=update_success sensor=sensor-01 client=20004 hostname=sensor-01 v_from=2.0.2 v_to=2.0.3 rollback=false details=...
```

---

## Operações — Passo a Passo

### Publicar nova versão

```bash
cd /Users/senna/WORK/Sensores-Updates

# 1. Faça as alterações em sensor/scripts/, sensor/configs/, etc.
git add .
git commit -m "feat: descrição da mudança"
git push origin main

# 2. Crie e publique a tag (dispara o CI)
git tag v2.0.4
git push origin v2.0.4

# 3. Acompanhe o CI (~2 minutos)
gh run watch

# 4. Sincronize o manifest.json atualizado pelo CI
git pull origin main

# 5. Verifique o release publicado
gh release view v2.0.4
```

> **Regra de versionamento:**
> - `PATCH` (2.0.X): ajustes de scripts/configs, sem mudança estrutural
> - `MINOR` (2.X.0): novas funcionalidades, novos serviços
> - `MAJOR` (X.0.0): mudanças incompatíveis, requer intervenção manual

---

### Forçar atualização imediata em todos os sensores

Útil após publicar uma versão crítica, sem aguardar o próximo ciclo do timer.

```bash
for IP in 172.16.162.191 172.16.162.192 172.16.162.193 172.16.162.136; do
  ssh -n -p 12222 root@$IP "systemctl start vigilant-updater.service" &
done
wait
```

Para um sensor específico:
```bash
ssh -p 12222 root@172.16.162.191 "systemctl start vigilant-updater.service"
```

---

### Instalar o updater em um sensor novo (completo)

Para sensores sendo instalados do zero. Requer o script `vigilant-sensor-install.sh`.

```bash
# No sensor (via SSH):
scp vigilant-sensor-install.sh root@IP_SENSOR:/tmp/
ssh -t root@IP_SENSOR "bash /tmp/vigilant-sensor-install.sh"
```

O instalador solicitará interativamente:
- Hostname do sensor (ex: `sensor-05`)
- Vigilant ID / Client ID (ex: `20004`)
- IP da central de logs (ex: `172.16.162.189`)
- Credenciais VPN e demais configurações

---

### Instalar somente o updater em sensor legado

Para sensores já configurados que apenas precisam do mecanismo de atualização.

```bash
ssh -t -p 12222 root@IP_SENSOR \
  "curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/tools/install-updater-only.sh \
   -o /tmp/install-updater-only.sh && bash /tmp/install-updater-only.sh"
```

O script detecta automaticamente `sensor_id`, `client_id` e `log_server_ip` existentes, oferecendo manter os valores atuais (Enter) ou substituir.

---

### Verificar versão atual de um sensor

```bash
# Versão instalada
ssh -p 12222 root@IP_SENSOR "cat /vigilant/scripts/vigilantsensor/updater/VERSION"

# Status do timer
ssh -p 12222 root@IP_SENSOR "systemctl list-timers | grep vigilant"

# Log dos últimos updates
ssh -p 12222 root@IP_SENSOR "tail -20 /vigilant/scripts/vigilantsensor/logs/vigilant-update.log | jq ."

# Identidade do sensor
ssh -p 12222 root@IP_SENSOR "cat /vigilant/scripts/sensor_id && cat /vigilant/scripts/vigilant_client_id"
```

---

### Alternar entre timer de teste e produção

| Timer | Intervalo | Uso |
|---|---|---|
| `vigilant-updater-test.timer` | A cada 1 hora | Desenvolvimento e validação |
| `vigilant-updater.timer` | Domingo 03h (+5min random) | Produção |

```bash
# Mudar para produção
ssh -p 12222 root@IP_SENSOR "
  systemctl disable vigilant-updater-test.timer
  systemctl stop vigilant-updater-test.timer
  systemctl enable vigilant-updater.timer
  systemctl start vigilant-updater.timer
  systemctl list-timers | grep vigilant
"

# Voltar para teste
ssh -p 12222 root@IP_SENSOR "
  systemctl disable vigilant-updater.timer
  systemctl stop vigilant-updater.timer
  systemctl enable vigilant-updater-test.timer
  systemctl start vigilant-updater-test.timer
"
```

---

## Monitoramento — Grafana

**URL:** `https://172.16.162.189`
**Login:** `admin` / senha configurada no setup

### Painéis disponíveis

| Painel | Descrição |
|---|---|
| **Total de Updates** | Contagem de `update_success` no período selecionado |
| **Rollbacks** | Contagem de rollbacks automáticos |
| **Falhas de Verificação** | Pacotes rejeitados por falha de SHA256 ou GPG |
| **Sensores Ativos** | Sensores com atividade no período (threshold: verde ≥ 3, vermelho = 0) |
| **Sensores sem Atividade (24h)** | Alerta vermelho quando sensor some por mais de 24h |
| **Log de Eventos** | Stream em tempo real com filtros por Cliente, Sensor, Evento |
| **Eventos por Sensor** | Barchart de distribuição de eventos por sensor |
| **Timeline de Updates** | Série temporal de update_success, rollback, verify_failed |
| **Atividade por Sensor** | Tabela: total de eventos por sensor no período |
| **Último Heartbeat** | Tabela com checagens nas últimas 24h — célula verde/vermelha por sensor |
| **Versão Atual por Sensor** | Versão em execução nos últimos 30 minutos por sensor |

### Atualizar o dashboard após mudanças no repositório

```bash
# No servidor de logs:
curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/server/grafana-dashboard.json \
  -o /etc/grafana/provisioning/dashboards/grafana-dashboard.json

PASS='SENHA_GRAFANA'
curl -s -u "admin:${PASS}" -X POST \
  http://localhost:3000/api/admin/provisioning/dashboards/reload
```

---

## Infraestrutura de Referência

| Componente | IP | Função |
|---|---|---|
| vigilant-logs | `172.16.162.189` | Servidor central: rsyslog, Loki, Promtail, Grafana, Nginx |
| sensor-001 | `172.16.162.191` | Sensor NDR (sensor_id: sensor-1, client: 20004) |
| sensor-002 | `172.16.162.192` | Sensor NDR (sensor_id: sensor-2, client: 20004) |
| sensor-003 | `172.16.162.193` | Sensor NDR (sensor_id: sensor-3, client: 20004) |
| sensor-004 | `172.16.162.136` | Sensor NDR (sensor_id: sensor-04, client: 20004) |

**Portas:**
- SSH nos sensores: `12222`
- rsyslog central: `514/TCP`
- Loki: `3100` (interno)
- Grafana: `443/HTTPS` (via Nginx)

---

## Segurança

### Verificação em duas camadas

Todo pacote distribuído passa por:

1. **SHA256** — garante integridade do arquivo baixado (sem corrupção ou truncamento)
2. **GPG (assinatura detached)** — garante autenticidade: apenas quem possui a chave privada `updater@vigilant.com.br` pode gerar um pacote aceito pelos sensores

Pacote com qualquer falha de verificação é **rejeitado sem instalação**, event `verify_failed` é reportado e o sensor permanece na versão anterior.

### Chave GPG

| Arquivo | Local | Visibilidade |
|---|---|---|
| `vigilant.pub.gpg` | `updater/` (no repo) | Pública — commitada no repositório |
| `vigilant-private.key.asc` | Somente no GitHub Secret `GPG_PRIVATE_KEY` | Privada — **nunca no repositório** |

Para regenerar as chaves (apenas se comprometidas):
```bash
cd /Users/senna/WORK/Sensores-Updates
./tools/generate-gpg-key.sh
# Output: tools/vigilant-private.key.asc (não commitar)
#         updater/vigilant.pub.gpg (commitar)

gh secret set GPG_PRIVATE_KEY < tools/vigilant-private.key.asc
git add updater/vigilant.pub.gpg
git commit -m "security: rotate GPG key"
git push origin main
```

> Após rotação, todos os sensores precisam receber a nova `vigilant.pub.gpg` via um release intermediário publicado ainda com a chave antiga.

---

## Troubleshooting

| Sintoma | Causa provável | Diagnóstico | Solução |
|---|---|---|---|
| `fetch_failed` | URL do manifest incorreta ou sem rede | `curl -v URL_MANIFEST` no sensor | Verificar `MANIFEST_URL` em `vigilant-updater.sh` |
| `verify_failed` | Chave GPG do sensor desatualizada | `cat /vigilant/scripts/vigilantsensor/updater/vigilant.pub.gpg` | Republicar release com chave correta |
| `jq not installed` | `jq` ausente no sensor | `which jq` | `dnf install -y jq` |
| `post_install_skip` | `post-install.sh` não encontrado no pacote | `tar -tzf sensor-pack.tar.gz | head` | Verificar `tools/pack-release.sh` |
| `no_update` constante | Sensor já na versão mais recente | Esperado | Publicar nova versão via tag |
| `rollback` frequente | Serviço falha após update | `journalctl -u snort -n 50` | Investigar conflito de config |
| Grafana sem dados | rsyslog não encaminha para central | `systemctl status rsyslog` no sensor | `systemctl restart rsyslog` |
| Sensor ausente no Grafana | `sensor_id` ou `client_id` não configurados | `cat /vigilant/scripts/sensor_id` | Criar arquivos de identidade manualmente |
| CI push rejeitado | manifest.json conflita com main | Verificar Actions log | `git pull --rebase origin main && git push` |

### Verificar logs completos de um ciclo de update

```bash
# No sensor — log do updater (JSON):
tail -50 /vigilant/scripts/vigilantsensor/logs/vigilant-update.log | jq .

# No sensor — saída do systemd:
journalctl -u vigilant-updater.service -n 50

# No servidor central — log recebido via rsyslog:
tail -50 /var/log/vigilant/sensor-updates.log

# No servidor — verificar ingestão no Loki:
curl -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="vigilant-updater"}' \
  --data-urlencode 'limit=10' | jq '.data.result[].values[][1]'
```

---

## Fluxo de Adição de Novos Arquivos/Configs

Para distribuir um novo arquivo a todos os sensores:

1. Adicionar o arquivo em `sensor/scripts/` ou `sensor/configs/<servico>/`
2. O `post-install.sh` copia automaticamente para o destino correto
3. Se a operação exige lógica adicional (cron, restart de serviço específico, substituição de variável), adicionar em `sensor/custom-deploy.sh`
4. Commitar, tagear e publicar:

```bash
git add sensor/
git commit -m "feat: adiciona novo script XYZ"
git tag v2.0.X && git push origin main && git push origin v2.0.X
```

Os sensores receberão o arquivo automaticamente no próximo ciclo do timer (ou imediatamente se forçado via `systemctl start vigilant-updater.service`).
