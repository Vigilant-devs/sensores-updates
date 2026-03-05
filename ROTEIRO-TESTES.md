# Roteiro de Testes — Vigilant Sensor Update System

**Versão atual em produção:** `v2.0.3`
**Repositório:** `Vigilant-devs/sensores-updates`
**Servidor de logs:** `https://IP_SERVIDOR_DE_LOGS` (Grafana)

---

## Visão Geral do Fluxo

```
Desenvolvedor                     GitHub                         Sensor
    │                                │                              │
    ├─ 1. Adiciona/edita arquivo     │                              │
    │    em sensor/scripts/          │                              │
    │                                │                              │
    ├─ 2. git add + git commit       │                              │
    │                                │                              │
    ├─ 3. git tag vX.Y.Z             │                              │
    │                                │                              │
    ├─ 4. git push origin main       │                              │
    ├─ 5. git push origin vX.Y.Z ───►│                              │
    │                                │ CI: empacota + assina        │
    │                                │ CI: cria Release             │
    │                                │ CI: atualiza manifest.json   │
    │                                │                              │
    │                                │◄──── sensor busca manifest ──┤
    │                                │                              │
    │                                │──── download + verificação ──►│
    │                                │                              ├─ post-install.sh
    │                                │                              ├─ scripts copiados
    │                                │                              └─ log enviado ao Grafana
```

---

## Parte 1 — Publicar uma Nova Versão (Desenvolvedor)

### 1.1 Estrutura de pastas do repositório

```
sensores-updates/
├── sensor/
│   ├── scripts/          ← scripts que vão para /vigilant/scripts/ no sensor
│   ├── configs/
│   │   ├── snort/        ← vai para /etc/snort/
│   │   ├── dionaea/      ← vai para /etc/dionaea/
│   │   ├── cowrie/       ← vai para /home/cowrie/cowrie/etc/
│   │   ├── bettercap/    ← vai para /etc/bettercap/
│   │   └── exabgp/       ← vai para /etc/exabgp/
│   ├── post-install.sh   ← executado após extração do pacote
│   └── custom-deploy.sh  ← hook opcional para lógica customizada
├── updater/              ← motor do atualizador (deployado no sensor)
├── manifest.json         ← aponta versão atual (atualizado automaticamente pelo CI)
└── tools/                ← scripts utilitários (pack, sign)
```

### 1.2 Como o post-install.sh funciona

O `post-install.sh` é o script que efetivamente **copia os arquivos do pacote para os destinos corretos no sensor**. Ele é chamado automaticamente pelo `vigilant-updater.sh` após o download e verificação do pacote — nunca precisa ser executado manualmente.

**Fluxo interno de uma atualização:**

```
vigilant-updater.sh
    │
    ├─ 1. Consulta manifest.json → nova versão disponível?
    ├─ 2. Baixa sensor-pack.tar.gz do GitHub Releases
    ├─ 3. Verifica SHA256 e assinatura GPG
    ├─ 4. Extrai em /vigilant/scripts/vigilantsensor/releases/vX.Y.Z/
    │
    └─ 5. Chama post-install.sh <release_dir> /vigilant
              │
              ├─ scripts/   → /vigilant/scripts/          (chmod +x em todos .sh)
              ├─ configs/snort/     → /etc/snort/
              ├─ configs/dionaea/   → /etc/dionaea/
              ├─ configs/cowrie/    → /home/cowrie/cowrie/etc/
              ├─ configs/bettercap/ → /etc/bettercap/
              ├─ configs/exabgp/    → /etc/exabgp/
              ├─ removals.txt       → remove arquivos listados do sensor (opcional)
              └─ custom-deploy.sh   → hook para lógica extra (opcional)
```

**O que colocar em cada lugar:**

| O que você quer fazer | Onde colocar no repositório |
|---|---|
| Adicionar/atualizar um script de operação | `sensor/scripts/` |
| Atualizar regras do Snort | `sensor/configs/snort/rules/` |
| Atualizar config do Cowrie | `sensor/configs/cowrie/` |
| Remover um arquivo obsoleto do sensor | `sensor/removals.txt` (um caminho absoluto por linha) |
| Executar comandos específicos nesta versão | `sensor/custom-deploy.sh` |

> **Importante:** o `post-install.sh` sobrescreve arquivos existentes sem confirmação.
> Se um subdiretório de `configs/` estiver vazio no pacote, ele é ignorado (não apaga nada no sensor).

### 1.3 Adicionar ou modificar um arquivo

**Exemplo:** adicionar um script `meu-script.sh` no sensor.

```bash
# Na sua máquina local, na raiz do repositório
cd /caminho/para/sensores-updates

# Copie ou crie o script na pasta correta
cp /origem/meu-script.sh sensor/scripts/meu-script.sh

# Verifique o que mudou
git status
git diff --stat
```

> **Regra:** tudo dentro de `sensor/scripts/` vai parar em `/vigilant/scripts/` no sensor.
> Se for uma config de serviço, coloque em `sensor/configs/<servico>/`.

### 1.4 Atualizar o CHANGELOG

Edite `sensor/CHANGELOG.md` e adicione a entrada da nova versão **antes** de publicar o tag:

```markdown
## vX.Y.Z (YYYY-MM-DD)
- Adicionado meu-script.sh para [descrição do propósito]
```

### 1.5 Fazer commit e publicar o tag

```bash
# Adicionar os arquivos modificados
git add sensor/scripts/meu-script.sh
git add sensor/CHANGELOG.md

# Commit (sem Co-Authored-By)
git commit -m "feat: adicionar meu-script.sh — [descrição breve]"

# Criar o tag da nova versão (incrementar o número correto)
# Patch (correção/adição pequena):  v2.0.3 → v2.0.4
# Minor (nova funcionalidade):      v2.0.3 → v2.1.0
# Major (mudança grande/breaking):  v2.0.3 → v3.0.0
git tag v2.0.4

# Fazer push do commit e do tag
git push origin main
git push origin v2.0.4
```

### 1.6 Acompanhar o CI no GitHub

Após o push do tag:

1. Acesse: `https://github.com/Vigilant-devs/sensores-updates/actions`
2. Aguarde o workflow **"Build, Sign & Publish Release"** — leva ~1-2 minutos
3. Quando concluído (check verde), verifique:
   - `https://github.com/Vigilant-devs/sensores-updates/releases` — nova release criada
   - `manifest.json` no repositório — versão atualizada para `v2.0.4`

> **Atenção:** O `manifest.json` é atualizado automaticamente pelo CI.
> **Nunca edite o `manifest.json` manualmente.**

---

## Parte 2 — Testar a Atualização no Sensor (Testador)

### Pré-requisitos

- Acesso SSH ao sensor de teste (porta `12222`)
- Sensor deve estar com o updater instalado e rodando
- Servidor de logs acessível em `172.16.162.143`

### Sensores disponíveis para teste

| Sensor     | IP               | sensor_id  | client_id |
|------------|------------------|------------|-----------|
| sensor-1   | 172.16.162.197   | sensor-1   | 20004     |
| sensor-2   | 172.16.162.202   | sensor-2   | 20004     |
| sensor-3   | 172.16.162.198   | sensor-3   | 20004     |
| sensor-04  | 172.16.162.136   | sensor-04  | 20004     |

### 2.1 Verificar o estado atual do sensor

```bash
ssh -p 12222 root@172.16.162.197

# Versão instalada atualmente
cat /vigilant/scripts/vigilantsensor/updater/VERSION

# Identidade do sensor
cat /vigilant/scripts/sensor_id
cat /vigilant/scripts/vigilant_client_id

# Status do serviço do updater
systemctl status vigilant-updater.service

# Último log do updater
tail -30 /vigilant/scripts/vigilantsensor/logs/vigilant-update.log
```

### 2.2 Disparar a atualização manualmente

O updater roda automaticamente (timer semanal em produção), mas para testes:

```bash
# Forçar execução imediata
systemctl start vigilant-updater.service

# Acompanhar em tempo real
journalctl -u vigilant-updater.service -f
```

Aguarde a conclusão (alguns segundos a ~1 minuto dependendo da conexão).

### 2.3 Verificar se a atualização foi aplicada

```bash
# Versão agora deve ser a nova (ex: 2.0.4)
cat /vigilant/scripts/vigilantsensor/updater/VERSION

# Verificar se o novo script está no lugar certo
ls -la /vigilant/scripts/meu-script.sh

# Ver o log completo do evento
tail -50 /vigilant/scripts/vigilantsensor/logs/vigilant-update.log
```

**O que esperar no log (formato JSON):**

```json
{"timestamp":"...","sensor":"sensor-1","client":"20004","event":"update_success","version_from":"2.0.3","version_to":"2.0.4","details":"..."}
```

Eventos possíveis:

| Evento           | Significado                                              |
|------------------|----------------------------------------------------------|
| `no_update`      | Sensor já está na versão mais recente — nenhuma ação     |
| `update_success` | Atualização aplicada com sucesso                         |
| `rollback`       | Falha detectada — versão anterior restaurada             |
| `verify_failed`  | Checksum ou assinatura GPG inválida — pacote rejeitado   |

### 2.4 Confirmar no Grafana

Acesse: `https://172.16.162.189`
Login: `admin` / (senha definida na instalação)

Painel **"Vigilant Sensor Updates"**:

- **Total de Updates** — deve incrementar em +1
- **Log de Eventos** — evento `update_success` com `version_to: 2.0.4`
- **Versão Atual por Sensor** — coluna "Versao" deve mostrar `2.0.4`

---

## Parte 3 — Cenários de Teste

### Cenário A — Script novo adicionado

**Objetivo:** verificar que um script novo chega ao sensor corretamente.

1. Adicione `sensor/scripts/teste-novo.sh` com conteúdo simples (`echo "ok"`)
2. Publique a versão conforme Parte 1
3. Dispare o updater no sensor conforme Parte 2
4. Verifique: `ls -la /vigilant/scripts/teste-novo.sh` — deve existir e ter permissão `+x`

### Cenário B — Script existente modificado

**Objetivo:** verificar que uma modificação sobrescreve o arquivo no sensor.

1. Edite um script existente em `sensor/scripts/` (ex: adicione um comentário)
2. Publique nova versão
3. No sensor, anote o conteúdo atual: `cat /vigilant/scripts/firewall.sh | head -5`
4. Dispare o updater
5. Verifique que o arquivo foi atualizado: `cat /vigilant/scripts/firewall.sh | head -5`

### Cenário C — Sensor já na versão mais recente

**Objetivo:** verificar que o updater não faz nada desnecessário.

1. Com o sensor já na versão mais recente, dispare o updater novamente
2. O log deve mostrar evento `no_update`
3. Versão não muda

### Cenário D — Atualização agendada (timer)

**Objetivo:** verificar que o timer automático está funcionando.

Primeiro, verifique se o timer está ativo:

```bash
systemctl status vigilant-updater.timer
```

**Se aparecer `inactive (dead)` ou `disabled`**, o timer não está habilitado. Para ativar:

```bash
# Timer de produção (domingo às 03:00)
systemctl enable --now vigilant-updater.timer

# Confirmar que está agendado
systemctl list-timers | grep vigilant
```

**Para testes mais rápidos**, use o timer de teste (a cada 5 minutos):

```bash
systemctl enable --now vigilant-updater-test.timer
systemctl list-timers | grep vigilant
```

> Use apenas um dos timers por vez:
> ```bash
> systemctl disable --now vigilant-updater.timer
> systemctl enable  --now vigilant-updater-test.timer
> ```

Para disparar imediatamente sem depender do timer:

```bash
systemctl start vigilant-updater.service
journalctl -u vigilant-updater.service -f
```

---

## Parte 4 — Troubleshooting

### Updater não executa

```bash
# Ver erro do serviço
systemctl status vigilant-updater.service
journalctl -u vigilant-updater.service --no-pager -n 50

# Verificar conectividade com GitHub
curl -s https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/manifest.json | jq .
```

### Atualização não chega (evento no_update quando deveria atualizar)

```bash
# Versão local
cat /vigilant/scripts/vigilantsensor/updater/VERSION

# Versão no manifest (o que o sensor vê)
curl -s https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/manifest.json | jq .version

# Se forem iguais: CI ainda não terminou, aguarde e tente novamente
# Se forem diferentes: inspecionar log completo para ver o motivo
```

### Evento verify_failed no log

```bash
# O pacote foi baixado mas a assinatura GPG ou SHA256 não batem
# Possíveis causas:
# 1. CI falhou no step de assinatura (verificar no GitHub Actions)
# 2. Chave pública no sensor está desatualizada

# Ver chave pública no sensor
ls -la /vigilant/scripts/vigilantsensor/updater/vigilant.pub.gpg
```

### Logs não aparecem no Grafana

```bash
# No sensor: verificar se o rsyslog está encaminhando
systemctl status rsyslog
cat /etc/rsyslog.d/50-vigilant-updater.conf

# No servidor de logs: verificar recebimento
tail -20 /var/log/vigilant/sensor-updates.log
systemctl status promtail
```

---

## Referência Rápida — Comandos Frequentes

```bash
# --- No sensor ---

# Ver versão atual
cat /vigilant/scripts/vigilantsensor/updater/VERSION

# Forçar atualização agora
systemctl start vigilant-updater.service

# Ver log em tempo real
journalctl -u vigilant-updater.service -f

# Ver log de eventos do updater
tail -f /vigilant/scripts/vigilantsensor/logs/vigilant-update.log

# --- Na máquina do desenvolvedor ---

# Publicar nova versão
git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z

# Verificar manifest após CI
curl -s https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/manifest.json | python3 -m json.tool

# Verificar release criada
# Acesse: https://github.com/Vigilant-devs/sensores-updates/releases
```
