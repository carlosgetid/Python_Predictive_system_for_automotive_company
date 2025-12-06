#!/bin/bash

# --- CORRECCIÓN DE RUTAS ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/retraining.log"
API_URL="http://127.0.0.1:5000/api/v1/trigger_retraining"

mkdir -p "$SCRIPT_DIR/logs"

echo "[$(date)] --- Iniciando Worker de Reentrenamiento (2 min) ---" >> "$LOG_FILE"

while true; do
    echo "[$(date)] Ejecutando Reentrenamiento..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 600 -X POST "$API_URL")
    
    echo "[$(date)] Respuesta: $response" >> "$LOG_FILE"
    sleep 120
done