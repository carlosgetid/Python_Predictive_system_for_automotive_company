#!/bin/bash

# Rutas dinámicas
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
MODELS_DIR="$PROJECT_ROOT/models"
DATA_DIR="$PROJECT_ROOT/data_fuente"
LOGS_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOGS_DIR/cleanup.log"

# --- CORRECCIÓN CRÍTICA: Apuntar al Python del Entorno Virtual ---
PYTHON_EXEC="$PROJECT_ROOT/venv/bin/python"

# 0. Borrar Logs Antiguos (NUEVO)
# Limpiamos la carpeta de logs antes de generar el nuevo reporte
if [ -d "$LOGS_DIR" ]; then
    # Borra todo el contenido dentro de logs/ (archivos .log anteriores)
    rm -rf "$LOGS_DIR"/*
fi

# Asegurar directorio de logs (se recrea si no existe)
mkdir -p "$LOGS_DIR"

echo "[$(date)] --- INICIANDO TAREA DE LIMPIEZA DE ENTORNO ---" >> "$LOG_FILE"

# 1. Borrar Modelos Físicos (.joblib, .keras)
if [ -d "$MODELS_DIR" ]; then
    echo "[$(date)] Eliminando archivos en $MODELS_DIR..." >> "$LOG_FILE"
    rm -rf "$MODELS_DIR"/*
    touch "$MODELS_DIR/.gitkeep"
    echo "[$(date)] ✅ Archivos de modelos eliminados." >> "$LOG_FILE"
else
    echo "[$(date)] ⚠️  Directorio models/ no encontrado." >> "$LOG_FILE"
fi

# 2. Borrar Datos de PostgreSQL (ACTUALIZADO)
echo "[$(date)] Iniciando limpieza de Base de Datos (PostgreSQL)..." >> "$LOG_FILE"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "[$(date)] ❌ ERROR CRÍTICO: No se encontró el entorno virtual." >> "$LOG_FILE"
    exit 1
fi

# Llamada al script Python que contiene la lógica TRUNCATE CASCADE para Postgres
"$PYTHON_EXEC" "$SCRIPT_DIR/utils_reset_db.py" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] ✅ Base de datos reseteada correctamente." >> "$LOG_FILE"
else
    echo "[$(date)] ❌ ERROR al resetear la base de datos." >> "$LOG_FILE"
    exit 1
fi

# 3. Borrar Archivos de Datos (Data Fuente)
echo "[$(date)] Iniciando limpieza de carpetas de datos..." >> "$LOG_FILE"

for folder in "entrada" "procesados" "fallidos"; do
    target_dir="$DATA_DIR/$folder"
    if [ -d "$target_dir" ]; then
        rm -rf "$target_dir"/*
        touch "$target_dir/.gitkeep"
        echo "[$(date)] ✅ Limpiado: $target_dir" >> "$LOG_FILE"
    else
        mkdir -p "$target_dir"
        echo "[$(date)] ⚠️  Creado: $target_dir" >> "$LOG_FILE"
    fi
done

echo "[$(date)] --- LIMPIEZA COMPLETADA ---" >> "$LOG_FILE"