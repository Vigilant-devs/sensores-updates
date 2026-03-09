O plano está completo para essa configuração. Veja o resumo do que será feito:

Fase 1: Criar /WORK/Sensores-Updates/ com todos os arquivos, ajustar MANIFEST_URL no updater, criar novo repo GitHub
Fase 2: Gerar novo par GPG, adicionar secrets no novo repo
Fase 3: Publicar primeiro release via tag → CI empacota, assina, publica automaticamente
Fase 4: Configurar servidor novo do zero com setup-log-server.sh (Loki + Promtail + Grafana + rsyslog + nginx)
Fase 5: Instalar updater nos sensores apontando para o novo repo
Fase 6: Configurar identidade (sensor_id + client_id) em cada sensor
Fase 7: Validar Grafana com filtro Cliente, logs chegando, updates funcionando
Fase 8: Trocar timer de teste (5min) para produção (semanal domingo 3h)
O que você faz manualmente:

Criar o repo no GitHub (gh repo create ou via UI)
Rodar tools/generate-gpg-key.sh localmente
Adicionar os 2 secrets (GPG_PRIVATE_KEY + GPG_PASSPHRASE) no GitHub
Provisionar a VM do novo servidor e rodar setup-log-server.sh
Rodar o vigilant-sensor-install.sh em cada sensor
O que está pronto e não muda:

Todo o código (updater, pack, CI, dashboard) — só copia do repo atual
Apenas 2 valores precisam ser ajustados: URL do manifest e IP do servidor de logs
Claude’s Plan
Procedimento Completo — Vigilant Sensor Update System
O que será feito
Criar o repositório /WORK/Sensores-Updates/ do zero com todos os arquivos do sistema,
configurar o GitHub, gerar chaves GPG, configurar o servidor de logs, instalar nos sensores
e validar o fluxo completo de atualização remota.

STATUS DAS FASES
Fase	Descrição	Status
1	Criar repositório local + GitHub	A FAZER
2	Gerar chave GPG + GitHub Secrets	A FAZER
3	Publicar primeiro release (CI/CD)	A FAZER
4	Configurar servidor de logs (central-update)	JÁ FEITO — reutilizar 172.16.162.193
5	Instalar updater nos sensores	A FAZER (script pronto)
6	Configurar identidade (sensor_id + client_id)	A FAZER nos sensores
7	Validar Grafana	A FAZER
FASE 1 — Repositório local e GitHub
1.1 Criar estrutura local

cd /Users/senna/WORK
mkdir -p Sensores-Updates
cd Sensores-Updates
git init
1.2 Copiar todos os arquivos do repo existente

ORIGEM="/Users/senna/WORK/vigilant-sensor-updater"
DESTINO="/Users/senna/WORK/Sensores-Updates"

# Estrutura de diretórios
mkdir -p .github/workflows sensor/scripts sensor/configs/{snort/rules,dionaea,cowrie,exabgp,bettercap} updater server tools

# Workflow CI/CD
cp "$ORIGEM/.github/workflows/release.yml" .github/workflows/

# Sensor — scripts e configs
cp -r "$ORIGEM/sensor/scripts/." sensor/scripts/
cp -r "$ORIGEM/sensor/configs/." sensor/configs/
cp "$ORIGEM/sensor/post-install.sh" sensor/
cp "$ORIGEM/sensor/custom-deploy.sh" sensor/

# Updater
cp "$ORIGEM/updater/vigilant-updater.sh" updater/
cp "$ORIGEM/updater/vigilant-updater.service" updater/
cp "$ORIGEM/updater/vigilant-updater.timer" updater/
cp "$ORIGEM/updater/vigilant-updater-test.timer" updater/
cp "$ORIGEM/updater/rsyslog-sensor.conf" updater/
# NÃO copiar: vigilant.pub.gpg (será gerado), .gh-token (não existe mais)

# Server
cp "$ORIGEM/server/setup-log-server.sh" server/
cp "$ORIGEM/server/rsyslog-server.conf" server/
cp "$ORIGEM/server/loki-config.yaml" server/
cp "$ORIGEM/server/promtail-config.yaml" server/
cp "$ORIGEM/server/grafana-datasource.yaml" server/
cp "$ORIGEM/server/grafana-dashboard.json" server/

# Tools
cp "$ORIGEM/tools/generate-gpg-key.sh" tools/
cp "$ORIGEM/tools/pack-release.sh" tools/
cp "$ORIGEM/tools/sign-release.sh" tools/

# Raiz
cp "$ORIGEM/.gitignore" .
1.3 Criar manifest.json inicial

cat > manifest.json << 'EOF'
{
  "version": "1.0.0",
  "released_at": "1970-01-01T00:00:00Z",
  "download_url": "",
  "sha256": "",
  "gpg_sig_url": "",
  "min_supported_version": "1.0.0",
  "rollback_safe": true,
  "changelog": "Initial placeholder — will be updated on first release"
}
EOF
1.4 IMPORTANTE: Atualizar a URL do manifest no updater
Editar updater/vigilant-updater.sh linha 28:


# Trocar:
MANIFEST_URL="https://raw.githubusercontent.com/Vigilant-devs/vigilant-sensor-updater/main/manifest.json"
# Por:
MANIFEST_URL="https://raw.githubusercontent.com/SEU_ORG/SEU_REPO/main/manifest.json"
1.5 Criar repositório no GitHub

gh repo create SEU_ORG/SEU_REPO --public --description "Vigilant Sensor Remote Updater"
git remote add origin https://github.com/SEU_ORG/SEU_REPO.git
git add .
git commit -m "chore: initial repository setup"
git push -u origin main
FASE 2 — Chave GPG + GitHub Secrets
2.1 Gerar chave GPG (UMA VEZ APENAS)

cd /Users/senna/WORK/Sensores-Updates
chmod +x tools/generate-gpg-key.sh
./tools/generate-gpg-key.sh
Output esperado:

tools/vigilant-private.key.asc → chave privada (GITIGNORED, nunca commitar)
updater/vigilant.pub.gpg → chave pública (commitar no repo)
2.2 Verificar e commitar a chave pública

gpg --list-secret-keys updater@vigilant.com.br
git add updater/vigilant.pub.gpg
git commit -m "chore: add GPG public key for package verification"
git push origin main
2.3 Adicionar secrets no GitHub

# Chave privada (conteúdo do arquivo .asc)
gh secret set GPG_PRIVATE_KEY < tools/vigilant-private.key.asc

# Passphrase (vazia porque generate-gpg-key.sh usa %no-protection)
gh secret set GPG_PASSPHRASE --body ""
Verificar:


gh secret list
# deve mostrar: GPG_PRIVATE_KEY e GPG_PASSPHRASE
FASE 3 — Primeiro release
3.1 Adicionar scripts do sensor
Coloque seus scripts em sensor/scripts/ e configs em sensor/configs/.
Para o primeiro release, os arquivos já copiados são suficientes.

3.2 Publicar o primeiro release via tag

git tag v1.0.0
git push origin v1.0.0
3.3 Acompanhar o CI/CD

gh run list --limit 5
gh run watch   # aguarda o workflow completar
O que o CI faz automaticamente:

Empacota sensor/ em sensor-pack.tar.gz
Assina com GPG (usando secrets.GPG_PRIVATE_KEY)
Cria GitHub Release com 3 assets: .tar.gz, .sig, .sha256
Atualiza manifest.json e commita de volta ao main
3.4 Verificar o release

gh release view v1.0.0
cat manifest.json   # deve ter version: "1.0.0" e URLs do GitHub
FASE 4 — Servidor de logs (central-update)
Se reutilizando o servidor existente (172.16.162.193): já configurado. Pular para Fase 5.

Se for um servidor novo:

4.1 Verificar pré-requisitos

# No servidor (Rocky Linux 10 mínimo):
cat /etc/os-release   # confirmar Rocky Linux
uname -m              # confirmar x86_64
4.2 Editar configurações no script antes de executar
Em server/setup-log-server.sh:


SERVER_HOSTNAME="vigilant-logs"
TIMEZONE="America/Sao_Paulo"
SENSOR_IP_RANGE=""              # ou "172.16.x.0/24" para restringir
GRAFANA_ADMIN_PASSWORD="SUA_SENHA_AQUI"
4.3 Executar setup

# Copiar para o servidor
scp server/setup-log-server.sh root@IP_SERVIDOR:/tmp/
scp server/grafana-dashboard.json root@IP_SERVIDOR:/tmp/
scp server/grafana-datasource.yaml root@IP_SERVIDOR:/tmp/
scp server/promtail-config.yaml root@IP_SERVIDOR:/tmp/
scp server/loki-config.yaml root@IP_SERVIDOR:/tmp/
scp server/rsyslog-server.conf root@IP_SERVIDOR:/tmp/

# No servidor:
bash /tmp/setup-log-server.sh
4.4 Verificar stack

systemctl status rsyslog loki promtail grafana-server nginx
# Todos devem estar: active (running)
Acesso: https://IP_SERVIDOR → login: admin / senha configurada

FASE 5 — Instalação do updater nos sensores
5.1 Ajustar o script de instalação
Em vigilant-sensor-install.sh (repo Andamento):


# Atualizar:
GITHUB_RAW="https://raw.githubusercontent.com/SEU_ORG/SEU_REPO/main"
LOG_SERVER="IP_DO_SERVIDOR_LOGS"
CURRENT_VERSION="1.0.0"   # mesma do primeiro release
5.2 Instalar em cada sensor

# Copiar e executar no sensor:
scp vigilant-sensor-install.sh root@IP_SENSOR:/tmp/
ssh root@IP_SENSOR "bash /tmp/vigilant-sensor-install.sh"
Inputs solicitados durante install:

Hostname: sensor-XX (ex: sensor-01)
Vigilant ID: ID_DO_CLIENTE (este valor vai para /vigilant/scripts/vigilant_client_id)
Key, Shield ID, VPN credentials...
5.3 Verificar instalação

# No sensor:
ls /vigilant/scripts/vigilantsensor/updater/
# deve ter: vigilant-updater.sh, vigilant.pub.gpg, VERSION

cat /vigilant/scripts/vigilantsensor/updater/VERSION
# deve mostrar: 1.0.0

systemctl status vigilant-updater-test.timer
# deve estar: active
FASE 6 — Configurar identidade do sensor
6.1 Arquivos de identidade
O install script já cria automaticamente. Para verificar:


# No sensor:
cat /vigilant/scripts/sensor_id          # ex: sensor-01
cat /vigilant/scripts/vigilant_client_id # ex: ID_DO_CLIENTE
Se precisar criar manualmente (sensores legados):


echo "sensor-01" > /vigilant/scripts/sensor_id
echo "ID_DO_CLIENTE" > /vigilant/scripts/vigilant_client_id
6.2 Forçar primeira execução

# No sensor:
systemctl start vigilant-updater.service
journalctl -u vigilant-updater.service -f
Log esperado (se já na versão mais recente):


event=no_update sensor=sensor-01 client=ID_DO_CLIENTE hostname=sensor-01 ...
FASE 7 — Validação no Grafana
7.1 Confirmar que logs chegam ao servidor

# No servidor central:
tail -f /var/log/vigilant/sensor-updates.log
# deve mostrar linhas com: event=no_update sensor=... client=...
7.2 Verificar labels no Loki

curl -s "http://localhost:3100/loki/api/v1/labels" | jq .
# deve incluir: client, sensor, event, hostname
7.3 Grafana
Acesse https://IP_SERVIDOR:

Filtro "Cliente": deve listar o(s) VIGILANT_ID dos sensores
Filtro "Sensor": cascateia pelo cliente selecionado
Sensores Ativos: deve mostrar contagem de sensores com log nas últimas 24h
Log de Eventos: mostra eventos em tempo real
7.4 Testar atualização automática

# 1. Fazer mudança qualquer em sensor/scripts/check.sh
# 2. Commitar e tagear:
git add . && git commit -m "test: bump para validar update"
git tag v1.0.1 && git push origin main && git push origin v1.0.1

# 3. Aguardar CI (2-3 min)
gh run watch

# 4. Em até 5 min, sensor detecta e aplica atualização
# Monitorar no sensor:
tail -f /vigilant/scripts/vigilantsensor/logs/vigilant-update.log | jq .

# 5. Confirmar no Grafana: event=update_success
FASE 8 — Transição para produção (quando pronto)
8.1 Trocar timer de teste (5min) para produção (semanal)

# No sensor:
systemctl disable vigilant-updater-test.timer
systemctl stop vigilant-updater-test.timer
systemctl enable vigilant-updater.timer   # domingo 3h
systemctl start vigilant-updater.timer
systemctl list-timers | grep vigilant
ARQUIVOS CRÍTICOS E SEUS PATHS
Arquivo no repo	Destino no sensor	Quem copia
updater/vigilant-updater.sh	/vigilant/scripts/vigilantsensor/updater/	Install script + self-update
updater/vigilant.pub.gpg	/vigilant/scripts/vigilantsensor/updater/	Install script
updater/vigilant-updater.service	/etc/systemd/system/	Install script
updater/vigilant-updater-test.timer	/etc/systemd/system/	Install script
updater/vigilant-updater.timer	/etc/systemd/system/	Install script
sensor/scripts/*	/vigilant/scripts/	post-install.sh (via pack)
sensor/configs/snort/	/etc/snort/	post-install.sh (via pack)
sensor/configs/cowrie/	/home/cowrie/cowrie/etc/	post-install.sh (via pack)
sensor/configs/dionaea/	/etc/dionaea/	post-install.sh (via pack)
updater/rsyslog-sensor.conf	/etc/rsyslog.d/50-vigilant-updater.conf	custom-deploy.sh (via pack)
updater/vigilant-updater.sh (no pack)	/vigilant/.../updater/vigilant-updater.sh	custom-deploy.sh (self-update)
TROUBLESHOOTING COMUM
Sintoma	Causa	Solução
jq not installed	jq ausente no sensor	dnf install -y jq
fetch_failed	manifest URL errado	Verificar MANIFEST_URL no updater.sh
verify_failed	Chave GPG errada	Regenerar chave e republicar
post_install_skip	tar com diretório top-level	Confirmar tar -C staging . no pack-release.sh
download_failed	Race condition manifest vs release	Release deve ser criado ANTES de atualizar manifest
CI push rejeitado	Conflito concurrent	O workflow usa git checkout origin/main antes de commitar
Grafana sem filtro "Cliente"	Promtail config antiga	Atualizar promtail-config.yaml + restart promtail
Filtro "Cliente" vazio	Arquivos de identidade não criados	Criar sensor_id e vigilant_client_id nos sensores
IMPLEMENTAÇÃO NO NOVO REPO
Passos que Claude vai executar:

Criar /WORK/Sensores-Updates/ e copiar todos os arquivos
Criar manifest.json inicial placeholder
Instruir o usuário a criar o GitHub repo + adicionar secrets manualmente
Documentar os valores que precisam ser personalizados (URL do manifest, IP do servidor)
Passos que o usuário faz manualmente:

Criar repo no GitHub (gh repo create ou via UI)
Executar tools/generate-gpg-key.sh
Adicionar GPG_PRIVATE_KEY e GPG_PASSPHRASE ao GitHub Secrets
Executar vigilant-sensor-install.sh nos sensores
Status geral do sistema existente (o que ainda falta no repo atual):

 Criar /vigilant/scripts/sensor_id e /vigilant/scripts/vigilant_client_id nos sensores
 Aplicar promtail-config.yaml atualizado no servidor (extrai label client)
 Aplicar grafana-dashboard.json atualizado no servidor (filtro Cliente)
 Aguardar v2.2.9 propagar (self-update do updater.sh)
 Verificar Grafana com filtro Cliente funcionando
User approved the plan
Update Todos

Fase 1: Criar estrutura local em /WORK/Sensores-Updates/ e copiar arquivos

Fase 1: Criar manifest.json placeholder e ajustar MANIFEST_URL

Fase 2: Gerar chave GPG e orientar sobre GitHub Secrets

Fase 3: Orientar publicacao do primeiro release
Bash Create Sensores-Updates directory and git init
IN
mkdir -p Sensores-Updates && cd Sensores-Updates && git init && echo "OK: git init em $(pwd)"

OUT
hint: Using 'master' as the name for the initial branch. This default branch name
hint: will change to "main" in Git 3.0. To configure the initial branch name
hint: to use in all of your new repositories, which will suppress this warning,
hint: call:
hint:
hint: 	git config --global init.defaultBranch <name>
hint:
hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
hint: 'development'. The just-created branch can be renamed via this command:
hint:
hint: 	git branch -m <name>
hint:
hint: Disable this message with "git config set advice.defaultBranchName false"
Initialized empty Git repository in /Users/senna/WORK/Sensores-Updates/.git/
OK: git init em /Users/senna/WORK/Sensores-Updates
Bash Set main as default branch
IN
git checkout -b main 2>/dev/null || git branch -m main && echo "branch: $(git branch)"

OUT
branch:
Bash Rename to main branch
IN
git branch -m main && echo "OK"

OUT
OK
Bash Copy all files from vigilant-sensor-updater to Sensores-Updates
IN
ORIGEM="/Users/senna/WORK/vigilant-sensor-updater"
DESTINO="/Users/senna/WORK/Sensores-Updates"

cd "$DESTINO"

# Estrutura de diretórios
mkdir -p .github/workflows \
         sensor/scripts \
         sensor/configs \
         updater \
         server \
         tools

# CI/CD
cp "$ORIGEM/.github/workflows/release.yml" .github/workflows/

# Sensor
cp -r "$ORIGEM/sensor/scripts/." sensor/scripts/
cp -r "$ORIGEM/sensor/configs/." sensor/configs/
cp "$ORIGEM/sensor/post-install.sh" sensor/
cp "$ORIGEM/sensor/custom-deploy.sh" sensor/

# Updater (sem chave pública — será gerada nova)
cp "$ORIGEM/updater/vigilant-updater.sh" updater/
cp "$ORIGEM/updater/vigilant-updater.service" updater/
cp "$ORIGEM/updater/vigilant-updater.timer" updater/
cp "$ORIGEM/updater/vigilant-updater-test.timer" updater/
cp "$ORIGEM/updater/rsyslog-sensor.conf" updater/

# Server
cp "$ORIGEM/server/setup-log-server.sh" server/
cp "$ORIGEM/server/rsyslog-server.conf" server/
cp "$ORIGEM/server/loki-config.yaml" server/
cp "$ORIGEM/server/promtail-config.yaml" server/
cp "$ORIGEM/server/grafana-datasource.yaml" server/
cp "$ORIGEM/server/grafana-dashboard.json" server/

# Tools
cp "$ORIGEM/tools/generate-gpg-key.sh" tools/
cp "$ORIGEM/tools/pack-release.sh" tools/
cp "$ORIGEM/tools/sign-release.sh" tools/

# Raiz
cp "$ORIGEM/.gitignore" .

echo "=== Arquivos copiados ==="
find . -not -path './.git/*' -type f | sort

OUT
=== Arquivos copiados ===
./.github/workflows/release.yml
./.gitignore
./sensor/configs/bettercap/.gitkeep
./sensor/configs/bettercap/better.conf
./sensor/configs/cowrie/.gitkeep
./sensor/configs/cowrie/cowrie.cfg
./sensor/configs/dionaea/.gitkeep
./sensor/configs/dionaea/dionaea.cfg
./sensor/configs/exabgp/.gitkeep
./sensor/configs/exabgp/exabgp.conf
./sensor/configs/snort/.gitkeep
./sensor/configs/snort/rules/.gitkeep
./sensor/configs/snort/rules/attack-responses.rules
./sensor/configs/snort/rules/backdoor.rules
./sensor/configs/snort/rules/bad-traffic.rules
./sensor/configs/snort/rules/black_list.rules
./sensor/configs/snort/rules/chat.rules
./sensor/configs/snort/rules/community-bot.rules
./sensor/configs/snort/rules/community-deleted.rules
./sensor/configs/snort/rules/community-dos.rules
./sensor/configs/snort/rules/community-exploit.rules
./sensor/configs/snort/rules/community-ftp.rules
./sensor/configs/snort/rules/community-game.rules
./sensor/configs/snort/rules/community-icmp.rules
./sensor/configs/snort/rules/community-imap.rules
./sensor/configs/snort/rules/community-inappropriate.rules
./sensor/configs/snort/rules/community-mail-client.rules
./sensor/configs/snort/rules/community-misc.rules
./sensor/configs/snort/rules/community-nntp.rules
./sensor/configs/snort/rules/community-oracle.rules
./sensor/configs/snort/rules/community-policy.rules
./sensor/configs/snort/rules/community-sip.rules
./sensor/configs/snort/rules/community-smtp.rules
./sensor/configs/snort/rules/community-sql-injection.rules
./sensor/configs/snort/rules/community-virus.rules
./sensor/configs/snort/rules/community-web-attacks.rules
./sensor/configs/snort/rules/community-web-cgi.rules
./sensor/configs/snort/rules/community-web-client.rules
./sensor/configs/snort/rules/community-web-dos.rules
./sensor/configs/snort/rules/community-web-iis.rules
./sensor/configs/snort/rules/community-web-misc.rules
./sensor/configs/snort/rules/community-web-php.rules
./sensor/configs/snort/rules/ddos.rules
./sensor/configs/snort/rules/deleted.rules
./sensor/configs/snort/rules/dns.rules
./sensor/configs/snort/rules/dos.rules
./sensor/configs/snort/rules/experimental.rules
./sensor/configs/snort/rules/exploit.rules
./sensor/configs/snort/rules/finger.rules
./sensor/configs/snort/rules/ftp.rules
./sensor/configs/snort/rules/icmp-info.rules
./sensor/configs/snort/rules/icmp.rules
./sensor/configs/snort/rules/imap.rules
./sensor/configs/snort/rules/info.rules
./sensor/configs/snort/rules/local.rules
./sensor/configs/snort/rules/misc.rules
./sensor/configs/snort/rules/multimedia.rules
./sensor/configs/snort/rules/mysql.rules
./sensor/configs/snort/rules/netbios.rules
./sensor/configs/snort/rules/nntp.rules
./sensor/configs/snort/rules/oracle.rules
./sensor/configs/snort/rules/other-ids.rules
./sensor/configs/snort/rules/p2p.rules
./sensor/configs/snort/rules/policy.rules
./sensor/configs/snort/rules/pop2.rules
./sensor/configs/snort/rules/pop3.rules
./sensor/configs/snort/rules/porn.rules
./sensor/configs/snort/rules/rpc.rules
./sensor/configs/snort/rules/rservices.rules
./sensor/configs/snort/rules/scan.rules
./sensor/configs/snort/rules/shellcode.rules
./sensor/configs/snort/rules/smtp.rules
./sensor/configs/snort/rules/snmp.rules
./sensor/configs/snort/rules/sql.rules
./sensor/configs/snort/rules/telnet.rules
./sensor/configs/snort/rules/tftp.rules
./sensor/configs/snort/rules/virus.rules
./sensor/configs/snort/rules/web-attacks.rules
./sensor/configs/snort/rules/web-cgi.rules
./sensor/configs/snort/rules/web-client.rules
./sensor/configs/snort/rules/web-coldfusion.rules
./sensor/configs/snort/rules/web-frontpage.rules
./sensor/configs/snort/rules/web-iis.rules
./sensor/configs/snort/rules/web-misc.rules
./sensor/configs/snort/rules/web-php.rules
./sensor/configs/snort/rules/white_list.rules
./sensor/configs/snort/rules/x11.rules
./sensor/configs/snort/snort.conf
./sensor/custom-deploy.sh
./sensor/post-install.sh
./sensor/scripts/check.sh
./sensor/scripts/cron.sh
./sensor/scripts/firewall.sh
./sensor/scripts/snort.sh
./sensor/scripts/update-exabgp-config.sh
./sensor/scripts/update-exabgp-localip.sh
./sensor/scripts/vigilant-healthcheck.sh
./sensor/scripts/vigilantagent.sh
./server/grafana-dashboard.json
./server/grafana-datasource.yaml
./server/loki-config.yaml
./server/promtail-config.yaml
./server/rsyslog-server.conf
./server/setup-log-server.sh
./tools/generate-gpg-key.sh
./tools/pack-release.sh
./tools/sign-release.sh
./updater/rsyslog-sensor.conf
./updater/vigilant-updater-test.timer
./updater/vigilant-updater.service
./updater/vigilant-updater.sh
./updater/vigilant-updater.timer
Todos os arquivos copiados. Agora crio o manifest.json placeholder e marco o MANIFEST_URL para ser substituído:

Write manifest.json
11 lines
{
  "version": "1.0.0",
  "released_at": "1970-01-01T00:00:00Z",
  "download_url": "",
  "sha256": "",
  "gpg_sig_url": "",
  "min_supported_version": "1.0.0",
  "rollback_safe": true,
  "changelog": "Initial placeholder — will be updated on first release"
}
Update Todos

Fase 1: Criar estrutura local em /WORK/Sensores-Updates/ e copiar arquivos

Fase 1: Criar manifest.json placeholder e ajustar MANIFEST_URL

Fase 2: Gerar chave GPG e orientar sobre GitHub Secrets

Fase 3: Orientar publicacao do primeiro release
Agora preciso do nome do GitHub org/repo que você vai usar para substituir a URL no updater/vigilant-updater.sh. Qual será o nome do novo repositório?

Formato: ORGANIZACAO/NOME-DO-REPO
Exemplo: Vigilant-devs/sensor-updater-v2 ou SeuUsuario/vigilant-updater



FASE 1 — Finalizar: criar o repo GitHub e fazer push

cd /Users/senna/WORK/Sensores-Updates
gh repo create Vigilant-devs/sensores-updates --public --description "Vigilant Sensor Remote Updater"
git remote add origin https://github.com/Vigilant-devs/sensores-updates.git
git push -u origin main
FASE 2 — Gerar chave GPG + adicionar secrets

cd /Users/senna/WORK/Sensores-Updates
chmod +x tools/generate-gpg-key.sh
./tools/generate-gpg-key.sh
Vai criar:

tools/vigilant-private.key.asc (nunca commitar — já está no .gitignore)
updater/vigilant.pub.gpg (commitar)

git add updater/vigilant.pub.gpg
git commit -m "chore: add GPG public key for package verification"
git push origin main


# Resposta: 
senna@MacBook-Pro-de-senna Sensores-Updates % ./tools/generate-gpg-key.sh

========================================================
  Vigilant Sensor — GPG Key Pair Generator
========================================================

  Name   : Vigilant Sensor Updater
  Email  : updater@vigilant.com.br
  Type   : RSA 4096
  Expiry : 2y

[WARN] A key for updater@vigilant.com.br already exists in your keyring.
Overwrite? (y/N): y
[1/4] Generating RSA 4096 key pair...
gpg: certificado de revogação armazenado como '/Users/senna/.gnupg/openpgp-revocs.d/792E230311C46F5732902CA437D535EE45411225.rev'
[OK] Key generated.

  Fingerprint: 792E230311C46F5732902CA437D535EE45411225

[2/4] Exporting public key → /Users/senna/WORK/Sensores-Updates/updater/vigilant.pub.gpg
[OK] Public key exported.
[3/4] Exporting private key → /Users/senna/WORK/Sensores-Updates/tools/vigilant-private.key.asc
[OK] Private key exported (chmod 600).

========================================================
  NEXT STEPS
========================================================

  1. Add private key to GitHub Secrets:
     Secret name : GPG_PRIVATE_KEY
     Secret value: contents of tools/vigilant-private.key.asc

  2. Add GPG passphrase to GitHub Secrets:
     Secret name : GPG_PASSPHRASE
     Secret value: (leave empty if you used %no-protection above)

  3. The public key is already at:
     /Users/senna/WORK/Sensores-Updates/updater/vigilant.pub.gpg
     → Commit it to the repository (it is safe to be public)

  4. NEVER commit the private key (tools/*.asc is in .gitignore)

  5. Store the private key file securely (password manager, etc.)

  Fingerprint: 792E230311C46F5732902CA437D535EE45411225
========================================================



# Adicionar os 2 secrets no GitHub:
gh secret set GPG_PRIVATE_KEY < tools/vigilant-private.key.asc
gh secret set GPG_PASSPHRASE --body ""



FASE 3 — Primeiro release

git tag v1.0.0
git push origin v1.0.0

# Acompanhar CI/CD (leva ~2 min):
gh run watch

Verifique as runs recentes:


gh run list --limit 5

Quando terminar, confirme:


cat manifest.json   # deve ter version: "1.0.0" e URLs do GitHub
gh release view v1.0.0
Me avise quando cada fase terminar para continuarmos com o servidor e os sensores.

O workflow atualizou o manifest.json no GitHub, mas sua cópia local ainda está desatualizada. Faça pull:


git pull origin main
cat manifest.json


Status das Fases
Fase	Status
1 — Repositório local + GitHub	✅ Concluída
2 — Chave GPG + GitHub Secrets	✅ Concluída
3 — Primeiro release (v1.0.0)	✅ Concluída
4 — Servidor de logs	A fazer
5 — Instalar updater nos sensores	A fazer
6 — Configurar identidade (sensor_id + client_id)	A fazer
7 — Validar Grafana	A fazer


Fase 4 — Servidor de logs

Vou verificar o script de setup do servidor antes de executar:

Read setup-log-server.sh
O script está pronto. Antes de copiar para o servidor, defina a senha do Grafana no arquivo:

Read setup-log-server.sh
Edite o script localmente e defina a senha antes de enviar:


# Edite a linha 30 do setup-log-server.sh:
# GRAFANA_ADMIN_PASSWORD="CHANGE_ME"
# → coloque a senha que quiser usar
Quando estiver com a senha definida, envie e execute no servidor:


cd /Users/senna/WORK/Sensores-Updates

# Copiar todos os arquivos do servidor
scp server/setup-log-server.sh \
    server/rsyslog-server.conf \
    server/loki-config.yaml \
    server/promtail-config.yaml \
    server/grafana-datasource.yaml \
    server/grafana-dashboard.json \
    root@172.16.162.189:/tmp/

# Executar no servidor
ssh root@172.16.162.189 "bash /tmp/setup-log-server.sh"

# Depois, no terminal conectado ao servidor execute:
bash /tmp/setup-log-server.sh


# Acessar: 
http://172.16.162.189
login: admin
Senha: Vigilant2026!@#$%


# Instalar os sensores
# Parametros a serem acertados dentro do script dos sensores: 
    local GITHUB_RAW="https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main"
    local CURRENT_VERSION="1.0.0"
    local LOG_SERVER="172.16.162.189"

    Definir quando configurado o Grafanna o ip publico dele. 


# Quando terminar, execute em cada sensor para verificar:


# Checar instalação do updater
ls /vigilant/scripts/vigilantsensor/updater/
cat /vigilant/scripts/vigilantsensor/updater/VERSION
cat /vigilant/scripts/sensor_id
cat /vigilant/scripts/vigilant_client_id

# Checar timer ativo
systemctl status vigilant-updater-test.timer


# Caso o instalador nao instalou o updater rode: 
O install rodou mas não chamou install_vigilant_updater — o script usado foi o da raiz (/WORK/vigilant-sensor-install.sh) que não tem essa função. O sensor está instalado normalmente, só falta o updater.

Instale manualmente no sensor agora:


# 1. Criar diretórios
mkdir -p /vigilant/scripts/vigilantsensor/updater
mkdir -p /vigilant/scripts/vigilantsensor/logs

# 2. Baixar arquivos do updater do novo repo
GITHUB_RAW="https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main"
UPDATER_DIR="/vigilant/scripts/vigilantsensor/updater"

for f in updater/vigilant-updater.sh updater/vigilant.pub.gpg updater/vigilant-updater.service updater/vigilant-updater-test.timer updater/vigilant-updater.timer; do
    curl -fsSL "${GITHUB_RAW}/${f}" -o "${UPDATER_DIR}/$(basename $f)" && echo "OK: $(basename $f)" || echo "FALHA: $(basename $f)"
done

# 3. Permissões e versão
chmod +x "${UPDATER_DIR}/vigilant-updater.sh"
echo "2.0.0" > "${UPDATER_DIR}/VERSION"

# 4. Identidade do sensor
echo "sensor-001" > /vigilant/scripts/sensor_id
echo "20004"      > /vigilant/scripts/vigilant_client_id
chmod 644 /vigilant/scripts/sensor_id /vigilant/scripts/vigilant_client_id

# 5. Systemd
cp "${UPDATER_DIR}/vigilant-updater.service"    /etc/systemd/system/
cp "${UPDATER_DIR}/vigilant-updater-test.timer" /etc/systemd/system/
cp "${UPDATER_DIR}/vigilant-updater.timer"      /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vigilant-updater-test.timer

# 6. rsyslog → servidor central
cat > /etc/rsyslog.d/50-vigilant-updater.conf << 'EOF'
if $programname == 'vigilant-updater' then @@172.16.162.189:514
& stop
EOF
systemctl restart rsyslog

echo "=== Updater instalado ==="
cat "${UPDATER_DIR}/VERSION"
systemctl status vigilant-updater-test.timer --no-pager




