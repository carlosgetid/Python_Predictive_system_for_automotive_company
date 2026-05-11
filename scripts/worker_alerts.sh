#!/bin/bash
# Worker para gatillar el Job de generación de alertas diarias

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/alerts.log"
INTERVAL_FILE="$SCRIPT_DIR/pids/worker_alerts.interval"
API_URL="http://localhost:5000/api/jobs/generate-alerts"

mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/pids"

# Intervalo por defecto: 3 minutos
DEFAULT_MINUTES=3

echo "[$(date)] --- Iniciando Worker de Alertas ---" >> "$LOG_FILE"

while true; do
    # Leer intervalo actual (en minutos) desde el archivo de config
    if [ -f "$INTERVAL_FILE" ]; then
        SLEEP_MINUTES=$(cat "$INTERVAL_FILE" 2>/dev/null)
    else
        SLEEP_MINUTES=$DEFAULT_MINUTES
    fi

    # Validar que sea un número positivo
    if ! [[ "$SLEEP_MINUTES" =~ ^[0-9]+$ ]] || [ "$SLEEP_MINUTES" -lt 1 ]; then
        SLEEP_MINUTES=$DEFAULT_MINUTES
    fi

    SLEEP_SECONDS=$((SLEEP_MINUTES * 60))

    echo "[$(date)] Ejecutando verificación de Alertas (HU-007 & HU-012) — intervalo: ${SLEEP_MINUTES} min..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL")
    echo "[$(date)] Respuesta del backend: $response" >> "$LOG_FILE"

    sleep "$SLEEP_SECONDS"
done
