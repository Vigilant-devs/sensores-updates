# Scripts Vigilant
scp -P 12222 root@172.16.162.191:/vigilant/scripts/firewall.sh              /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/cron.sh                  /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/vigilantagent.sh         /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/keepalive.sh             /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/snort.sh                 /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/update-exabgp-config.sh  /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/
scp -P 12222 root@172.16.162.191:/vigilant/scripts/update-exabgp-localip.sh /Users/senna/WORK/vigilant-sensor-updater/sensor/scripts/

# Configs
scp -P 12222 root@172.16.162.191:/etc/snort/snort.conf                      /Users/senna/WORK/vigilant-sensor-updater/sensor/configs/snort/
scp -P 12222 root@172.16.162.191:/etc/dionaea/dionaea.cfg                   /Users/senna/WORK/vigilant-sensor-updater/sensor/configs/dionaea/
scp -P 12222 root@172.16.162.191:/home/cowrie/cowrie/etc/cowrie.cfg          /Users/senna/WORK/vigilant-sensor-updater/sensor/configs/cowrie/
scp -P 12222 root@172.16.162.191:/etc/exabgp/exabgp.conf                    /Users/senna/WORK/vigilant-sensor-updater/sensor/configs/exabgp/



# O que o script toca mas NÃO deve entrar no update:

Arquivo	Por quê não versionar
/etc/ipsec.conf + /etc/ipsec.secrets	Contém IPs e senhas específicos por sensor
/etc/xl2tpd/xl2tpd.conf	Configuração VPN por sensor
/etc/ssh/sshd_config	Configurado uma vez na instalação
/etc/resolv.conf	DNS por ambiente
/etc/sysctl.conf	Parâmetros de kernel, uma vez só
/etc/crontab	Gerenciado pelo próprio cron.sh
/etc/sudoers	Segurança, não deve ser sobrescrito remotamente
Binários (snort, dionaea, cowrie...)	São instalados via RPM/tar, não via update de config


# Arquivos do snort 
scp -P 12222 -r root@172.16.162.191:/etc/snort/rules/ \
  /Users/senna/WORK/vigilant-sensor-updater/sensor/configs/snort/


# Suporte a Remover arquivos do snort: 
Pronto. Agora quando precisar remover um arquivo de todos os sensores:

1. Crie o arquivo sensor/removals.txt no repositório:

# Arquivos a remover nesta versão
/vigilant/scripts/script-antigo.sh
/etc/snort/rules/regra-obsoleta.rules
2. Commit + nova tag → sensores recebem a atualização e deletam os arquivos listados.

Na próxima versão você pode remover o removals.txt — ele só precisa existir na versão que faz a remoção. Versões seguintes sem ele simplesmente ignoram.




# Maquinas antigas sensores 

# Da sua máquina, para cada sensor antigo:
ssh -t -p 12222 root@172.16.162.136 \
  "curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/tools/install-updater-only.sh \
   -o /tmp/install-updater-only.sh && bash /tmp/install-updater-only.sh"


ssh -p 12222 root@172.16.162.136 "cat /vigilant/scripts/vigilantsensor/logs/vigilant-update.log"


# Para verificar a versao que o sensor esta verifique o arquivo: 
cat /vigilant/scripts/vigilantsensor/updater/VERSION

# Com mais contexto: 
echo "versao : $(cat /vigilant/scripts/vigilantsensor/updater/VERSION)"
echo "sensor : $(cat /vigilant/scripts/sensor_id)"
echo "client : $(cat /vigilant/scripts/vigilant_client_id)"
echo "logs   : $(cat /vigilant/scripts/log_server_ip)"

# Onde é definido a versao do sensor? 

São dois lugares, dependendo de qual script instalou:
vigilant-sensor-install.sh (instalação completa) — linha 1485/1519:

local CURRENT_VERSION="2.0.0"   # ← hardcoded
echo "$CURRENT_VERSION" > "${UPDATER_DIR}/VERSION"


Em sensores legados: 
tools/install-updater-only.sh (sensores legados) — busca do manifest no momento da instalação:

MANIFEST_VERSION=$(curl ... manifest.json | grep '"version"' ...)
echo "$MANIFEST_VERSION" > "${UPDATER_DIR}/VERSION"


# Tag v2.0.1 publicada. O CI está rodando agora (~2 min). Acompanhe em:
https://github.com/Vigilant-devs/sensores-updates/actions

Quando o CI terminar, o manifest.json será atualizado para v2.0.1 e os sensores vão detectar na próxima checagem (até 5 min). Para ver o momento exato que cada sensor atualiza, no servidor de logs:


tail -f /var/log/vigilant/sensor-updates.log | grep -E "update_started|update_success|update_failed"
Os sensores 1/2/3 estão em v2.0.0 e o sensor-04 em v1.0.6 — todos devem detectar v2.0.1 e aplicar o update.




# Definindo IP estatico no sensor:
nmcli con mod ens160 \
  ipv4.method manual \
  ipv4.addresses "172.16.162.189/24" \
  ipv4.gateway "172.16.162.2" \
  ipv4.dns "8.8.8.8"

nmcli con up ens160



# Sensores nao aparecem no grafana
# Checar: 

# Nos sensores: 
systemctl status vigilant-updater-test.timer && systemctl status vigilant-updater.service

systemctl enable vigilant-updater-test.timer && systemctl start vigilant-updater-test.timer


[root@sensor-3 ~]# cat /etc/rsyslog.d/50-vigilant-updater.conf
# =============================================================================
# Vigilant Sensor — rsyslog forwarding config
# File: /etc/rsyslog.d/50-vigilant-updater.conf
#
# Encaminha eventos do vigilant-updater ao servidor central de logs (TCP 514).
# O servidor central deve estar rodando o rsyslog-server.conf correspondente.
#
# Instalação no sensor:
#   cp updater/rsyslog-sensor.conf /etc/rsyslog.d/50-vigilant-updater.conf
#   systemctl restart rsyslog
# =============================================================================

# Encaminhar todos os logs do programa vigilant-updater via TCP para o servidor.
# @@ = TCP (mais confiável que UDP para canal de auditoria)

if $programname == 'vigilant-updater' then @@172.16.162.189:514
& stop


# Comando para verificar qual ip do Grafana:
cat /etc/rsyslog.d/50-vigilant-updater.conf 

# Comando para verificar as atualizacoes no Grafana
tail -f /var/log/vigilant/sensor-updates.log 


# Ver labels disponíveis no Loki agora
curl -s "http://localhost:3100/loki/api/v1/label/sensor/values" | python3 -m json.tool
{
    "status": "success",
    "data": [
        "sensor-04",
        "sensor-1",
        "sensor-2",
        "sensor-3"
    ]
}


