#!/bin/bash

# Rutas dinámicas
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
MODELS_DIR="$PROJECT_ROOT/models"
LOG_FILE="$SCRIPT_DIR/logs/cleanup.log"

# --- CORRECCIÓN CRÍTICA: Apuntar al Python del Entorno Virtual ---
# Asumimos que la carpeta 'venv' está en la raíz del proyecto
PYTHON_EXEC="$PROJECT_ROOT/venv/bin/python"

# Asegurar directorio de logs
mkdir -p "$SCRIPT_DIR/logs"

echo "[$(date)] --- INICIANDO TAREA DE LIMPIEZA DE ENTORNO ---" >> "$LOG_FILE"

# 1. Borrar Modelos Físicos (.joblib, .keras)
if [ -d "$MODELS_DIR" ]; then
    echo "[$(date)] Eliminando archivos en $MODELS_DIR..." >> "$LOG_FILE"
    # Borra el contenido pero mantiene la carpeta
    rm -rf "$MODELS_DIR"/*
    # Opcional: Crear un .gitkeep para no perder la carpeta en git si está vacía
    touch "$MODELS_DIR/.gitkeep"
    echo "[$(date)] ✅ Archivos de modelos eliminados." >> "$LOG_FILE"
else
    echo "[$(date)] ⚠️  Directorio models/ no encontrado, nada que borrar." >> "$LOG_FILE"
fi

# 2. Borrar Datos de MySQL
echo "[$(date)] Iniciando limpieza de Base de Datos..." >> "$LOG_FILE"

# Validación de seguridad: Verificar si existe el entorno virtual
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "[$(date)] ❌ ERROR CRÍTICO: No se encontró el entorno virtual en:" >> "$LOG_FILE"
    echo "       $PYTHON_EXEC" >> "$LOG_FILE"
    echo "       El script intentó usar el python del sistema y falló por falta de librerías." >> "$LOG_FILE"
    exit 1
fi

# Ejecutamos el script de Python USANDO EL PYTHON DEL VENV
"$PYTHON_EXEC" "$SCRIPT_DIR/utils_reset_db.py" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] ✅ Base de datos reseteada correctamente." >> "$LOG_FILE"
else
    echo "[$(date)] ❌ ERROR al resetear la base de datos. Revisa los logs anteriores." >> "$LOG_FILE"
    exit 1
fi

echo "[$(date)] --- LIMPIEZA COMPLETADA ---" >> "$LOG_FILE"