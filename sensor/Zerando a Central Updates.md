ou verificar os paths de storage do Loki antes de dar os comandos.

Read loki-config.yaml
Tenho tudo. Rode isso no servidor 172.16.162.189:


# 1. Parar serviços que leem/escrevem os dados
systemctl stop promtail loki

# 2. Limpar todos os dados do Loki
rm -rf /var/lib/loki/chunks/*
rm -rf /var/lib/loki/index/*
rm -rf /var/lib/loki/index_cache/*
rm -rf /var/lib/loki/compactor/*

# 3. Zerar o arquivo de log do rsyslog (sem apagar o arquivo)
truncate -s 0 /var/log/vigilant/sensor-updates.log

# 4. Zerar o position file do Promtail (senão ele tenta ler do offset antigo)
truncate -s 0 /var/lib/promtail/positions.yaml

# 5. Reiniciar tudo
systemctl start loki promtail
systemctl status loki promtail
O que cada passo faz:

# 6. Aguardar o próximo ciclo e confirmar que dados chegam
tail -f /var/log/vigilant/sensor-updates.log


Passo	Efeito
chunks/*	Remove todos os blocos de log armazenados
index/*	Remove o índice TSDB (labels, streams)
index_cache/*	Remove cache de índice
compactor/*	Remove estado de compactação/retenção
sensor-updates.log	Zera o arquivo que o Promtail lê
positions.yaml	Reseta o cursor do Promtail (evita leitura de offset inválido)
Grafana (dashboards, datasources, painéis) não é afetado — esses ficam em /var/lib/grafana/grafana.db que não tocamos.

Depois de rodar, o Grafana aparecerá sem dados. Quando reinstalar e ligar os sensores, os novos eventos (com o IP correto da Central Updates) começarão a aparecer normalmente.

