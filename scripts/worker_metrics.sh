#!/bin/bash

# --- CORRECCIÓN DE RUTAS ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/metrics.log"
INTERVAL_FILE="$SCRIPT_DIR/pids/worker_metrics.interval"
API_URL="http://127.0.0.1:5000/api/v1/metrics"

mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/pids"

# Intervalo por defecto: 5 minutos
DEFAULT_MINUTES=5

echo "[$(date)] --- Iniciando Worker de Métricas ---" >> "$LOG_FILE"

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

    echo "[$(date)] Consultando Métricas (intervalo: ${SLEEP_MINUTES} min)..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_URL")
    echo "[$(date)] Respuesta: $response" >> "$LOG_FILE"

    sleep "$SLEEP_SECONDS"
done