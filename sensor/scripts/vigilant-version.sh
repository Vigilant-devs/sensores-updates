#!/bin/bash
# Vigilant Sensor — Version Info
# Deployed via remote updater (sensor-pack)

UPDATER_DIR="/vigilant/scripts/vigilantsensor/updater"

echo "=============================="
echo "  Vigilant Sensor — Version"
echo "=============================="
echo "  Sensor ID : $(cat /vigilant/scripts/sensor_id 2>/dev/null || hostname)"
echo "  Client ID : $(cat /vigilant/scripts/vigilant_client_id 2>/dev/null || echo 'unknown')"
echo "  Pack ver  : $(cat "${UPDATER_DIR}/VERSION" 2>/dev/null || echo 'unknown')"
echo "  Hostname  : $(hostname)"
echo "  Date      : $(date)"
echo "=============================="
