Adicionar novo sensor ao sistema

São 3 etapas simples. Substitua 172.16.162.XXX e sensor-02 pelos valores reais.

Etapa 1 — Instalar o updater no novo sensor

ssh -p 12222 root@172.16.162.XXX '
# Criar estrutura de diretórios
mkdir -p /vigilant/scripts/vigilantsensor/updater
mkdir -p /vigilant/scripts/vigilantsensor/logs

# Baixar arquivos do updater direto do GitHub (repo público)
cd /vigilant/scripts/vigilantsensor/updater

curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/vigilant-sensor-updater/main/updater/vigilant-updater.sh \
  -o vigilant-updater.sh && chmod +x vigilant-updater.sh

curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/vigilant-sensor-updater/main/updater/vigilant.pub.gpg \
  -o vigilant.pub.gpg

curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/vigilant-sensor-updater/main/updater/vigilant-updater.service \
  -o vigilant-updater.service

curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/vigilant-sensor-updater/main/updater/vigilant-updater-test.timer \
  -o vigilant-updater-test.timer

# Gravar versão atual
echo "2.2.0" > VERSION

# Instalar serviços systemd
cp vigilant-updater.service /etc/systemd/system/
cp vigilant-updater-test.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable vigilant-updater-test.timer
systemctl start vigilant-updater-test.timer
echo "Updater instalado"
'
Etapa 2 — Configurar rsyslog para enviar logs ao central-update

ssh -p 12222 root@172.16.162.XXX '
cat > /etc/rsyslog.d/50-vigilant-updater.conf << EOF
if \$programname == '"'"'vigilant-updater'"'"' then @@172.16.162.190:514
& stop
EOF
systemctl restart rsyslog
echo "rsyslog configurado"
'
Etapa 3 — Verificar

# Forçar primeira execução
ssh -p 12222 root@172.16.162.XXX 'systemctl start vigilant-updater'

# Confirmar log no central-update
tail -f /var/log/vigilant/sensor-updates.log
Deve aparecer event=update_success sensor=sensor-02 ou event=no_update — ambos significam que está funcionando.

Resumo: baixar 4 arquivos, instalar systemd, configurar rsyslog. Sem token, sem configuração manual de versão — na primeira execução o updater já baixa e instala a versão atual automaticamente.

