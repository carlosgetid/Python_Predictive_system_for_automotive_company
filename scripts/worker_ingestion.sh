#!/bin/bash

# --- CORRECCIÓN DE RUTAS ---
# Obtenemos la ruta absoluta donde está este script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Apuntamos a la carpeta logs que está AL LADO del script
LOG_FILE="$SCRIPT_DIR/logs/ingestion.log"
API_URL="http://127.0.0.1:5000/api/v1/trigger_ingestion"

# Asegurar que la carpeta logs exista (por seguridad)
mkdir -p "$SCRIPT_DIR/logs"

echo "[$(date)] --- Iniciando Worker de Ingesta (1 min) ---" >> "$LOG_FILE"

while true; do
    echo "[$(date)] Ejecutando Ingesta..." >> "$LOG_FILE"
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL")
    
    echo "[$(date)] Respuesta: $response" >> "$LOG_FILE"
    sleep 60
done