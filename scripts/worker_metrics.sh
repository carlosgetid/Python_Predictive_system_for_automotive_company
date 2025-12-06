#!/bin/bash

# --- CORRECCIÓN DE RUTAS ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/metrics.log"
API_URL="http://127.0.0.1:5000/api/v1/metrics"

mkdir -p "$SCRIPT_DIR/logs"

echo "[$(date)] --- Iniciando Worker de Métricas (5 min) ---" >> "$LOG_FILE"

while true; do
    echo "[$(date)] Consultando Métricas..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_URL")
    
    echo "[$(date)] Respuesta: $response" >> "$LOG_FILE"
    sleep 300
done