#!/bin/bash
# Log file (JSON format)
LOG_FILE="/var/log/health-check.json"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# JSON log format
health_log() {
    local check_name="$1"
    local check_status="$2"
    local cmd="$3"
    shift 3

    local extra_fields=""

    for field in "$@"; do
        local key="${field%%=*}"
        local value="${field#*=}"
        extra_fields="${extra_fields}, \"${key}\": \"${value}\""
    done

    printf '{"event_type": "healthcheck", "check_name": "%s", "check_status": "%s", "command": "%s"%s}\n' \
        "$check_name" "$check_status" "$cmd" "$extra_fields" >> "$LOG_FILE"
}

# Function to display check on screen
show_check() {
    local status="$1"
    local desc="$2"
    local value="$3"

    case "$status" in
        OK)   printf "${GREEN}  ✔${NC} %-28s" "$desc" ;;
        FAIL) printf "${RED}  ✗${NC} %-28s" "$desc" ;;
        WARN) printf "${YELLOW}  ⚠${NC} %-28s" "$desc" ;;
    esac

    [ -n "$value" ] && printf ": %s\n" "$value" || printf "\n"
}

# Check write permission on log
[ ! -w "$(dirname "$LOG_FILE")" ] && [ ! -w "$LOG_FILE" ] && {
    echo "WARNING: No permission to write to $LOG_FILE"
    echo "Run with sudo: sudo $0"
    echo ""
}

# Execution date/time
EXEC_DATE=$(printf '%(%d-%m-%Y %H:%M:%S)T' -1)
echo "============================================"
echo "  Vigilant Health Check"
echo "  Execution: $EXEC_DATE"
echo "============================================"
echo ""

# Log execution start
health_log "EXECUTION_START" "OK" "check.sh" "exec_timestamp=${EXEC_DATE// /_}"

# ============================================================
# 1. SYSTEM IDENTIFICATION
# ============================================================
echo "=== System Identification ==="
echo ""

if [[ "$OSTYPE" == "linux"* ]]; then
    OS="Linux"
    while IFS='=' read -r key value; do
        [[ "$key" == "PRETTY_NAME" ]] && DISTRO="${value//\"/}" && break
    done < /etc/os-release 2>/dev/null

    if [ -n "$DISTRO" ]; then
        show_check "OK" "Operating System" "$OS"
        show_check "OK" "Distribution" "$DISTRO"
        health_log "OS_DETECTION" "OK" "cat /etc/os-release" "os_type=${OS}" "distro_name=${DISTRO// /_}"
    else
        show_check "WARN" "Operating System" "$OS"
        show_check "FAIL" "Distribution" "Not detected"
        health_log "OS_DETECTION" "FAIL" "cat /etc/os-release" "os_type=${OS}" "distro_name=unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    VERSION=$(sw_vers -productVersion 2>/dev/null)
    show_check "OK" "Operating System" "$OS"
    show_check "OK" "Version" "$VERSION"
    health_log "OS_DETECTION" "OK" "sw_vers -productVersion" "os_type=${OS}" "os_version=${VERSION}"
else
    OS="Unknown"
    show_check "FAIL" "Operating System" "$OS ($OSTYPE)"
    health_log "OS_DETECTION" "FAIL" "uname -s" "os_type=unknown" "ostype_raw=${OSTYPE}"
fi

echo ""

ARCH=$(uname -m 2>/dev/null || echo "unknown")
KERNEL=$(uname -r 2>/dev/null || echo "unknown")
HOSTNAME_VAL=$(hostname 2>/dev/null || echo "unknown")

[ "$ARCH" != "unknown" ] && show_check "OK" "Architecture" "$ARCH" || show_check "FAIL" "Architecture" "Not detected"
[ "$KERNEL" != "unknown" ] && show_check "OK" "Kernel" "$KERNEL" || show_check "FAIL" "Kernel" "Not detected"
[ "$HOSTNAME_VAL" != "unknown" ] && show_check "OK" "Hostname" "$HOSTNAME_VAL" || show_check "FAIL" "Hostname" "Not detected"

health_log "SYSTEM_INFO" "OK" "uname -m; uname -r; hostname" "sys_arch=${ARCH}" "kernel_version=${KERNEL}" "host_name=${HOSTNAME_VAL}"

echo ""

# ============================================================
# 2. AGENT VALIDATION
# ============================================================
echo "=== Agent Validation ==="
echo ""

get_agent_version() {
    if [ -x "/var/ossec/bin/wazuh-control" ]; then
        /var/ossec/bin/wazuh-control info 2>/dev/null | grep "WAZUH_VERSION" | cut -d'"' -f2
    elif [ -x "/opt/ossec/bin/wazuh-control" ]; then
        /opt/ossec/bin/wazuh-control info 2>/dev/null | grep "WAZUH_VERSION" | cut -d'"' -f2
    fi
}

AGENT_FOUND=false

if systemctl is-active --quiet wazuh-agent 2>/dev/null; then
    AGENT_FOUND=true
    AGENT_VERSION=$(get_agent_version)
    show_check "OK" "Agent" "Wazuh ${AGENT_VERSION:-version not detected}"
    show_check "OK" "Agent Service" "running"
    health_log "AGENT_CHECK" "OK" "systemctl status wazuh-agent" "agent_name=wazuh" "service_state=running" "agent_version=${AGENT_VERSION:-unknown}"
elif systemctl list-unit-files wazuh-agent.service 2>/dev/null | grep -q wazuh-agent; then
    AGENT_FOUND=true
    AGENT_VERSION=$(get_agent_version)
    show_check "OK" "Agent" "Wazuh ${AGENT_VERSION:-version not detected}"
    show_check "FAIL" "Agent Service" "stopped"
    health_log "AGENT_CHECK" "FAIL" "systemctl status wazuh-agent" "agent_name=wazuh" "service_state=stopped" "agent_version=${AGENT_VERSION:-unknown}"
fi

if [ "$AGENT_FOUND" = false ]; then
    if systemctl is-active --quiet vigilant-agent 2>/dev/null; then
        AGENT_FOUND=true
        AGENT_VERSION=$(get_agent_version)
        show_check "OK" "Agent" "Vigilant ${AGENT_VERSION:-version not detected}"
        show_check "OK" "Agent Service" "running"
        health_log "AGENT_CHECK" "OK" "systemctl status vigilant-agent" "agent_name=vigilant" "service_state=running" "agent_version=${AGENT_VERSION:-unknown}"
    elif systemctl list-unit-files vigilant-agent.service 2>/dev/null | grep -q vigilant-agent; then
        AGENT_FOUND=true
        AGENT_VERSION=$(get_agent_version)
        show_check "OK" "Agent" "Vigilant ${AGENT_VERSION:-version not detected}"
        show_check "FAIL" "Agent Service" "stopped"
        health_log "AGENT_CHECK" "FAIL" "systemctl status vigilant-agent" "agent_name=vigilant" "service_state=stopped" "agent_version=${AGENT_VERSION:-unknown}"
    fi
fi

if [ "$AGENT_FOUND" = false ]; then
    # Fallback for legacy systems without systemd (e.g. Ubuntu 14.04)
    for ossec_path in /var/ossec /opt/ossec; do
        if [ -x "$ossec_path/bin/wazuh-control" ]; then
            AGENT_FOUND=true
            AGENT_VERSION=$("$ossec_path/bin/wazuh-control" info 2>/dev/null | grep "WAZUH_VERSION" | cut -d'"' -f2)
            AGENT_STATUS=$("$ossec_path/bin/wazuh-control" status 2>/dev/null | grep -c "running")
            if [ "$AGENT_STATUS" -gt 0 ] 2>/dev/null; then
                show_check "OK" "Agent" "Wazuh ${AGENT_VERSION:-version not detected} (legacy)"
                show_check "OK" "Agent Service" "running (wazuh-control)"
                health_log "AGENT_CHECK" "OK" "wazuh-control status" "agent_name=wazuh" "service_state=running" "agent_version=${AGENT_VERSION:-unknown}" "detection=legacy"
            else
                show_check "OK" "Agent" "Wazuh ${AGENT_VERSION:-version not detected} (legacy)"
                show_check "FAIL" "Agent Service" "stopped (wazuh-control)"
                health_log "AGENT_CHECK" "FAIL" "wazuh-control status" "agent_name=wazuh" "service_state=stopped" "agent_version=${AGENT_VERSION:-unknown}" "detection=legacy"
            fi
            break
        fi
    done
fi

if [ "$AGENT_FOUND" = false ]; then
    show_check "FAIL" "Agent" "none installed"
    health_log "AGENT_CHECK" "FAIL" "systemctl/wazuh-control" "agent_name=none" "service_state=not_installed" "agent_installed=false"
fi

echo ""

# ============================================================
# 2.5. SCA (SECURITY CONFIGURATION ASSESSMENT) VALIDATION
# ============================================================
echo "=== SCA Configuration Assessment ==="
echo ""

SCA_FILES_FOUND=false
SCA_POLICY_COUNT=0

# Check SCA files in both locations
for sca_path in /var/ossec /opt/ossec; do
    if [ -d "$sca_path/ruleset/sca" ] && ls "$sca_path/ruleset/sca"/*.yml >/dev/null 2>&1; then
        SCA_FILES_FOUND=true
        SCA_POLICY_COUNT=$(ls -1 "$sca_path/ruleset/sca"/*.yml 2>/dev/null | wc -l)
        break
    fi
done

if [ "$SCA_FILES_FOUND" = true ]; then
    show_check "OK" "SCA Policies" "Loaded ($SCA_POLICY_COUNT policies)"

    # List each policy: name and file path
    SCA_POLICY_NAMES=""
    for sca_file in "$sca_path/ruleset/sca"/*.yml; do
        if [ -f "$sca_file" ]; then
            sca_name=$(grep -m1 '^[[:space:]]*name:' "$sca_file" 2>/dev/null | sed 's/^[[:space:]]*name:[[:space:]]*//' | tr -d '"'"'")
            if [ -n "$sca_name" ]; then
                show_check "OK" "SCA Policy" "$sca_name"
                printf "     %-28s: %s\n" "File Policy Path" "$sca_file"
                SCA_POLICY_NAMES="${SCA_POLICY_NAMES}${sca_name}|${sca_file};"
            else
                show_check "WARN" "SCA Policy" "$(basename "$sca_file") (name not found)"
                printf "     %-28s: %s\n" "File Policy Path" "$sca_file"
                SCA_POLICY_NAMES="${SCA_POLICY_NAMES}unknown|${sca_file};"
            fi
        fi
    done

    # Check last execution in logs
    SCA_EXEC_LOG=""
    for log_path in /var/ossec/logs/ossec.log /opt/ossec/logs/ossec.log; do
        if [ -f "$log_path" ] && grep -q "sca: INFO: Evaluation finished for policy" "$log_path" 2>/dev/null; then
            SCA_EXEC_LOG=$(grep "sca: INFO: Evaluation finished for policy" "$log_path" 2>/dev/null | tail -1)
            break
        fi
    done

    if [ -n "$SCA_EXEC_LOG" ]; then
        show_check "OK" "SCA Execution" "Active"
        health_log "SCA_CHECK" "OK" "grep sca logs" "sca_configured=true" "sca_policies=${SCA_POLICY_COUNT}" "sca_policy_details=${SCA_POLICY_NAMES}" "status=active"
    else
        show_check "WARN" "SCA Execution" "Not executed yet"
        health_log "SCA_CHECK" "WARN" "grep sca logs" "sca_configured=true" "sca_policies=${SCA_POLICY_COUNT}" "sca_policy_details=${SCA_POLICY_NAMES}" "status=waiting_first_execution"
    fi
else
    show_check "FAIL" "SCA Policies" "Not configured"
    health_log "SCA_CHECK" "FAIL" "ls sca directory" "sca_configured=false"
fi

echo ""

# ============================================================
# 3. SYSMON VALIDATION
# ============================================================
echo "=== Sysmon Validation ==="
echo ""

if command -v sysmon &> /dev/null; then
    SYSMON_VERSION=$(sysmon --version 2>&1 | grep -o "Sysmon v[0-9.]*" || echo "unknown")
    if systemctl is-active --quiet sysmon 2>/dev/null; then
        SYSMON_STATUS="running"
        SYSMON_STATUS_CHECK="OK"
    else
        SYSMON_STATUS="stopped"
        SYSMON_STATUS_CHECK="FAIL"
    fi
    show_check "OK" "Sysmon Installed" "$SYSMON_VERSION"
    show_check "$SYSMON_STATUS_CHECK" "Sysmon Service" "$SYSMON_STATUS"
    health_log "SYSMON_CHECK" "OK" "sysmon --version" "sysmon_installed=true" "sysmon_version=${SYSMON_VERSION// /_}" "service_state=${SYSMON_STATUS}"
else
    show_check "FAIL" "Sysmon Installed" "Not found"
    health_log "SYSMON_CHECK" "FAIL" "which sysmon" "sysmon_installed=false"
fi

SYSMON_LOGROTATE="/etc/logrotate.d/sysmon"
if [ -f "$SYSMON_LOGROTATE" ]; then
    show_check "OK" "Sysmon Logrotate" "$SYSMON_LOGROTATE"
    health_log "SYSMON_LOGROTATE" "OK" "test -f /etc/logrotate.d/sysmon" "logrotate_configured=true" "config_path=${SYSMON_LOGROTATE}"
else
    show_check "FAIL" "Sysmon Logrotate" "Not found"
    health_log "SYSMON_LOGROTATE" "FAIL" "test -f /etc/logrotate.d/sysmon" "logrotate_configured=false"
fi

SYSMON_LOG="/var/log/sysmon.log"
if [ -f "$SYSMON_LOG" ]; then
    show_check "OK" "Sysmon Log" "$SYSMON_LOG"
    health_log "SYSMON_LOG" "OK" "test -f /var/log/sysmon.log" "log_exists=true" "log_path=${SYSMON_LOG}"
else
    show_check "FAIL" "Sysmon Log" "Not found"
    health_log "SYSMON_LOG" "FAIL" "test -f /var/log/sysmon.log" "log_exists=false" "log_path=${SYSMON_LOG}"
fi

echo ""

# ============================================================
# 4. SNOOPY VALIDATION
# ============================================================
echo "=== Snoopy Validation ==="
echo ""

if command -v snoopyctl &> /dev/null; then
    SNOOPY_VERSION=$(snoopyctl version 2>/dev/null | head -1 || echo "unknown")
    if snoopyctl status 2>/dev/null | grep -qi "enabled"; then
        SNOOPY_STATUS="enabled"
        SNOOPY_STATUS_CHECK="OK"
    else
        SNOOPY_STATUS="disabled"
        SNOOPY_STATUS_CHECK="FAIL"
    fi
    show_check "OK" "Snoopy Installed" "$SNOOPY_VERSION"
    show_check "$SNOOPY_STATUS_CHECK" "Snoopy Service" "$SNOOPY_STATUS"
    health_log "SNOOPY_CHECK" "OK" "snoopyctl version" "snoopy_installed=true" "snoopy_version=${SNOOPY_VERSION// /_}" "service_state=${SNOOPY_STATUS}"
else
    show_check "FAIL" "Snoopy Installed" "Not found"
    health_log "SNOOPY_CHECK" "FAIL" "which snoopyctl" "snoopy_installed=false"
fi

SNOOPY_LOGROTATE="/etc/logrotate.d/snoopy"
if [ -f "$SNOOPY_LOGROTATE" ]; then
    show_check "OK" "Snoopy Logrotate" "$SNOOPY_LOGROTATE"
    health_log "SNOOPY_LOGROTATE" "OK" "test -f /etc/logrotate.d/snoopy" "logrotate_configured=true" "config_path=${SNOOPY_LOGROTATE}"
else
    show_check "FAIL" "Snoopy Logrotate" "Not found"
    health_log "SNOOPY_LOGROTATE" "FAIL" "test -f /etc/logrotate.d/snoopy" "logrotate_configured=false"
fi

SNOOPY_LOG="/var/log/snoopy.log"
if [ -f "$SNOOPY_LOG" ]; then
    show_check "OK" "Snoopy Log" "$SNOOPY_LOG"
    health_log "SNOOPY_LOG" "OK" "test -f /var/log/snoopy.log" "log_exists=true" "log_path=${SNOOPY_LOG}"
else
    show_check "FAIL" "Snoopy Log" "Not found"
    health_log "SNOOPY_LOG" "FAIL" "test -f /var/log/snoopy.log" "log_exists=false" "log_path=${SNOOPY_LOG}"
fi

echo ""

# ============================================================
# 4.4. SHIELD VALIDATION
# ============================================================
echo "=== Shield Validation ==="
echo ""

SHIELD_BIN=""
SHIELD_SERVICE_FILE="false"
SHIELD_SERVICE_STATE="not_installed"
if [ -x "/opt/ossec/shield/vigilant_shield" ]; then
	SHIELD_BIN="/opt/ossec/shield/vigilant_shield"
elif [ -x "/var/ossec/shield/vigilant_shield" ]; then
	SHIELD_BIN="/var/ossec/shield/vigilant_shield"
fi

if [ -n "$SHIELD_BIN" ]; then
	show_check "OK" "Shield Binary" "$SHIELD_BIN"
	health_log "SHIELD_BINARY" "OK" "test -x $SHIELD_BIN" "shield_binary=true" "binary_path=${SHIELD_BIN}"
else
	show_check "FAIL" "Shield Binary" "Not found"
	health_log "SHIELD_BINARY" "FAIL" "test -x /opt/ossec/shield/vigilant_shield || test -x /var/ossec/shield/vigilant_shield" "shield_binary=false"
fi

if [ -f "/etc/systemd/system/vigilant_shield.service" ]; then
	SHIELD_SERVICE_FILE="true"
	show_check "OK" "Shield Service File" "/etc/systemd/system/vigilant_shield.service"
	health_log "SHIELD_SERVICE_FILE" "OK" "test -f /etc/systemd/system/vigilant_shield.service" "service_file=true"

	if systemctl is-active --quiet vigilant_shield 2>/dev/null; then
		SHIELD_SERVICE_STATE="running"
		show_check "OK" "Shield Service" "running"
		health_log "SHIELD_SERVICE" "OK" "systemctl is-active vigilant_shield" "service_state=running"
	else
		SHIELD_SERVICE_STATE="stopped"
		show_check "FAIL" "Shield Service" "stopped"
		health_log "SHIELD_SERVICE" "FAIL" "systemctl is-active vigilant_shield" "service_state=stopped"
	fi
else
	show_check "FAIL" "Shield Service File" "Not found"
	show_check "FAIL" "Shield Service" "not installed"
	health_log "SHIELD_SERVICE_FILE" "FAIL" "test -f /etc/systemd/system/vigilant_shield.service" "service_file=false"
	health_log "SHIELD_SERVICE" "FAIL" "systemctl list-unit-files vigilant_shield.service" "service_state=not_installed"
fi

SHIELD_VERSION="unknown"
if [ -f "/opt/ossec/VERSION-SHIELD" ]; then
	SHIELD_VERSION=$(cat /opt/ossec/VERSION-SHIELD 2>/dev/null)
elif [ -f "/var/ossec/VERSION-SHIELD" ]; then
	SHIELD_VERSION=$(cat /var/ossec/VERSION-SHIELD 2>/dev/null)
fi

if [ "$SHIELD_VERSION" != "unknown" ] && [ -n "$SHIELD_VERSION" ]; then
	show_check "OK" "Shield Version" "$SHIELD_VERSION"
	health_log "SHIELD_VERSION" "OK" "cat VERSION-SHIELD" "version=${SHIELD_VERSION}"
else
	show_check "WARN" "Shield Version" "Not detected"
	health_log "SHIELD_VERSION" "WARN" "cat VERSION-SHIELD" "version=unknown"
fi

if [ -n "$SHIELD_BIN" ] && [ "$SHIELD_SERVICE_FILE" = "true" ] && [ "$SHIELD_SERVICE_STATE" = "running" ]; then
	show_check "OK" "Shield Check" "healthy"
	health_log "SHIELD_CHECK" "OK" "shield consolidated validation" \
		"shield_binary=true" \
		"service_file=${SHIELD_SERVICE_FILE}" \
		"service_state=${SHIELD_SERVICE_STATE}" \
		"version=${SHIELD_VERSION}"
else
	show_check "FAIL" "Shield Check" "unhealthy"
	health_log "SHIELD_CHECK" "FAIL" "shield consolidated validation" \
		"shield_binary=$( [ -n "$SHIELD_BIN" ] && echo true || echo false )" \
		"service_file=${SHIELD_SERVICE_FILE}" \
		"service_state=${SHIELD_SERVICE_STATE}" \
		"version=${SHIELD_VERSION}"
fi

echo ""

# ============================================================
# 4.5. SURICATA VALIDATION
# ============================================================
if command -v suricata &> /dev/null; then
    echo "=== Suricata Validation ==="
    echo ""

    SURICATA_VERSION=$(suricata -V 2>/dev/null | head -n1 | grep -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?' || echo "unknown")

    # Check installation
    show_check "OK" "SURICATA Installed" "suricata $SURICATA_VERSION"

    # Check service status
    if systemctl is-active --quiet suricata 2>/dev/null; then
        SURICATA_STATUS="running"
        SURICATA_STATUS_CHECK="OK"
    else
        SURICATA_STATUS="stopped"
        SURICATA_STATUS_CHECK="FAIL"
    fi
    show_check "$SURICATA_STATUS_CHECK" "Suricata Service" "$SURICATA_STATUS"

    # Check config file
    if [ -f /etc/suricata/suricata.yaml ]; then
        show_check "OK" "CONFIG suricata.yaml" "OK"
        CONFIG_STATUS="OK"
    else
        show_check "FAIL" "CONFIG suricata.yaml" "NOT FOUND"
        CONFIG_STATUS="NOT_FOUND"
    fi

    health_log "SURICATA_CHECK" "OK" "suricata -V" \
        "suricata_installed=true" \
        "suricata_version=$SURICATA_VERSION" \
        "service_state=$SURICATA_STATUS" \
        "config_status=$CONFIG_STATUS"

    echo ""
fi

# ============================================================
# 4.6. VIGILANT NETFLOW VALIDATION
# ============================================================
if command -v suricata &> /dev/null; then
    echo "=== Vigilant Netflow ==="
    echo ""

    # Check vigilant-ndr.timer (NDR Engines - runs every 1 min)
    if systemctl is-active --quiet vigilant-ndr.timer 2>/dev/null; then
        NDR_TIMER_STATUS="running"
        NDR_TIMER_CHECK="OK"
    elif systemctl is-enabled --quiet vigilant-ndr.timer 2>/dev/null; then
        NDR_TIMER_STATUS="enabled (waiting)"
        NDR_TIMER_CHECK="WARN"
    else
        NDR_TIMER_STATUS="inactive"
        NDR_TIMER_CHECK="FAIL"
    fi
    show_check "$NDR_TIMER_CHECK" "NDR Engines Timer" "$NDR_TIMER_STATUS"
    health_log "NETFLOW_NDR_TIMER" "$NDR_TIMER_CHECK" "systemctl status vigilant-ndr.timer" "service_state=$NDR_TIMER_STATUS"

    # Check nfcapd (NetFlow Collector)
    if systemctl is-active --quiet nfcapd 2>/dev/null; then
        NFCAPD_STATUS="running"
        NFCAPD_CHECK="OK"
    else
        NFCAPD_STATUS="stopped"
        NFCAPD_CHECK="FAIL"
    fi
    show_check "$NFCAPD_CHECK" "NFDump Collector (nfcapd)" "$NFCAPD_STATUS"
    health_log "NETFLOW_NFCAPD" "$NFCAPD_CHECK" "systemctl status nfcapd" "service_state=$NFCAPD_STATUS"

    # Check vigilant-ndr-nfdump-clean.timer (Cleanup - runs every 24h)
    if systemctl is-active --quiet vigilant-ndr-nfdump-clean.timer 2>/dev/null; then
        CLEAN_TIMER_STATUS="running"
        CLEAN_TIMER_CHECK="OK"
    elif systemctl is-enabled --quiet vigilant-ndr-nfdump-clean.timer 2>/dev/null; then
        CLEAN_TIMER_STATUS="enabled (waiting)"
        CLEAN_TIMER_CHECK="WARN"
    else
        CLEAN_TIMER_STATUS="inactive"
        CLEAN_TIMER_CHECK="FAIL"
    fi
    show_check "$CLEAN_TIMER_CHECK" "NFDump Cleanup Timer" "$CLEAN_TIMER_STATUS"
    health_log "NETFLOW_CLEANUP_TIMER" "$CLEAN_TIMER_CHECK" "systemctl status vigilant-ndr-nfdump-clean.timer" "service_state=$CLEAN_TIMER_STATUS"

    echo ""
fi

# ============================================================
# 5. CONNECTIVITY VALIDATION
# ============================================================
echo "=== Connectivity Validation ==="
echo ""

CURL_OUTPUT=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://vigilant.com.br 2>/dev/null)
CURL_EXIT=$?

if [ "$CURL_EXIT" -eq 0 ]; then
    if [[ "$CURL_OUTPUT" =~ ^[23][0-9][0-9]$ ]]; then
        show_check "OK" "Connectivity" "vigilant.com.br (HTTP $CURL_OUTPUT)"
        health_log "CONNECTIVITY" "OK" "curl -s https://vigilant.com.br" "target_host=vigilant.com.br" "http_code=${CURL_OUTPUT}"
    else
        show_check "WARN" "Connectivity" "vigilant.com.br (HTTP $CURL_OUTPUT)"
        health_log "CONNECTIVITY" "WARN" "curl -s https://vigilant.com.br" "target_host=vigilant.com.br" "http_code=${CURL_OUTPUT}"
    fi
else
    case $CURL_EXIT in
        6)  REASON="DNS_ERROR" ;;
        7)  REASON="CONNECTION_REFUSED" ;;
        28) REASON="TIMEOUT" ;;
        *)  REASON="ERROR_${CURL_EXIT}" ;;
    esac
    show_check "FAIL" "Connectivity" "vigilant.com.br ($REASON)"
    health_log "CONNECTIVITY" "FAIL" "curl -s https://vigilant.com.br" "target_host=vigilant.com.br" "error_reason=${REASON}"
fi

END_DATE=$(printf '%(%d-%m-%Y %H:%M:%S)T' -1)
health_log "EXECUTION_END" "OK" "check.sh" "exec_timestamp=${END_DATE// /_}"

echo ""
echo "============================================"
echo "  Finished: $END_DATE"
echo "  Log saved to: $LOG_FILE"
echo "============================================"
echo ""

    chmod +x /opt/check.sh
	echo -e "Check script successfully installed in /opt/check.sh"
    write_log "INFO" "Script /opt/check.sh installed successfully"