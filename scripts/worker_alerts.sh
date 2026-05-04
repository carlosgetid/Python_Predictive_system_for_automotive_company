#!/bin/bash
# Worker para gatillar el Job de generación de alertas diarias
# Ideal para ser ejecutado vía Cronjob, o mediante este loop integrado.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/logs/alerts.log"
API_URL="http://localhost:5000/api/jobs/generate-alerts"

mkdir -p "$SCRIPT_DIR/logs"

echo "[$(date)] --- Iniciando Worker de Alertas (3 min) ---" >> "$LOG_FILE"

while true; do
    echo "[$(date)] Ejecutando verificación de Alertas (HU-007 & HU-012)..." >> "$LOG_FILE"
    
    # Hacemos la peticion POST en background
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL")
    
    echo "[$(date)] Respuesta del backend: $response" >> "$LOG_FILE"
    
    # Dormir por 180 segundos (3 minutos)
    sleep 180
done
