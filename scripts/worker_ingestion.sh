#!/bin/bash

# --- CORRECCIÓN DE RUTAS ---
# Obtenemos la ruta absoluta donde está este script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Apuntamos a la carpeta logs que está AL LADO del script
LOG_FILE="$SCRIPT_DIR/logs/ingestion.log"
INTERVAL_FILE="$SCRIPT_DIR/pids/worker_ingestion.interval"
API_URL="http://127.0.0.1:5000/api/v1/trigger_ingestion"

# Asegurar que las carpetas existan
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/pids"

# Intervalo por defecto: 1 minuto (si no existe el archivo de config)
DEFAULT_MINUTES=1

echo "[$(date)] --- Iniciando Worker de Ingesta ---" >> "$LOG_FILE"

while true; do
    # Leer intervalo actual (en minutos) desde el archivo de config
    if [ -f "$INTERVAL_FILE" ]; then
        SLEEP_MINUTES=$(cat "$INTERVAL_FILE" 2>/dev/null)
    else
        SLEEP_MINUTES=$DEFAULT_MINUTES
    fi

    # Validar que sea un número positivo, si no, usar el default
    if ! [[ "$SLEEP_MINUTES" =~ ^[0-9]+$ ]] || [ "$SLEEP_MINUTES" -lt 1 ]; then
        SLEEP_MINUTES=$DEFAULT_MINUTES
    fi

    SLEEP_SECONDS=$((SLEEP_MINUTES * 60))

    echo "[$(date)] Ejecutando Ingesta (intervalo: ${SLEEP_MINUTES} min)..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL")
    echo "[$(date)] Respuesta: $response" >> "$LOG_FILE"

    sleep "$SLEEP_SECONDS"
done