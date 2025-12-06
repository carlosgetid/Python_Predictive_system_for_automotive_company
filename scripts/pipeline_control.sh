#!/bin/bash

# --- CONFIGURACIÓN DEL PIPELINE ---
# true: Borra modelos y datos al iniciar. | false: Inicia con el estado actual.
CLEANUP_ON_START=true
# ----------------------------------

# Directorios
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/pids"
LOG_DIR="$SCRIPT_DIR/logs"

# Crear directorios necesarios
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

start_worker() {
    local script_name=$1
    local pid_file="$PID_DIR/$script_name.pid"

    if [ -f "$pid_file" ]; then
        if kill -0 $(cat "$pid_file") 2>/dev/null; then
            echo "⚠️  $script_name ya está corriendo (PID: $(cat $pid_file))."
            return
        else
            rm "$pid_file"
        fi
    fi

    echo "🚀 Iniciando $script_name..."
    nohup "$SCRIPT_DIR/$script_name" > /dev/null 2>&1 &
    echo $! > "$pid_file"
    echo "   ✅ Iniciado con PID $(cat $pid_file)"
}

stop_worker() {
    local script_name=$1
    local pid_file="$PID_DIR/$script_name.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "🛑 Deteniendo $script_name (PID: $pid)..."
        pkill -P $pid 2>/dev/null
        kill $pid 2>/dev/null
        rm "$pid_file"
        echo "   ✅ Detenido."
    else
        echo "⚠️  $script_name no parece estar corriendo."
    fi
}

case "$1" in
    start)
        echo "=========================================="
        echo "   INICIANDO PIPELINE AUTOMATIZADO"
        echo "   Logs en: $LOG_DIR"
        echo "=========================================="

        # --- FASE 0: LIMPIEZA (Opcional) ---
        if [ "$CLEANUP_ON_START" = true ]; then
            echo "🧹 Ejecutando Tarea de Limpieza Inicial..."
            echo "   (Borrando modelos y vaciando BD...)"
            
            # Ejecutamos el script de limpieza y esperamos a que termine
            bash "$SCRIPT_DIR/task_cleanup.sh"
            
            if [ $? -eq 0 ]; then
                echo "   ✅ Limpieza terminada exitosamente."
            else
                echo "   ❌ Error en la limpieza. Revise logs/cleanup.log."
                echo "   ⚠️  Abortando inicio del pipeline por seguridad."
                exit 1
            fi
        else
            echo "ℹ️  Limpieza deshabilitada (CLEANUP_ON_START=false). Continuando con datos existentes."
        fi
        echo "------------------------------------------"

        # --- FASE 1: WORKERS ---
        start_worker "worker_ingestion.sh"
        start_worker "worker_retraining.sh"
        start_worker "worker_metrics.sh"
        echo "=========================================="
        ;;
    stop)
        echo "=========================================="
        echo "   APAGANDO PIPELINE AUTOMATIZADO"
        echo "=========================================="
        stop_worker "worker_ingestion.sh"
        stop_worker "worker_retraining.sh"
        stop_worker "worker_metrics.sh"
        echo "=========================================="
        ;;
    status)
        echo "Estado del Pipeline (Cleanup Flag: $CLEANUP_ON_START):"
        for script in "worker_ingestion.sh" "worker_retraining.sh" "worker_metrics.sh"; do
            if [ -f "$PID_DIR/$script.pid" ] && kill -0 $(cat "$PID_DIR/$script.pid") 2>/dev/null; then
                echo "🟢 $script: CORRIENDO (PID $(cat $PID_DIR/$script.pid))"
            else
                echo "🔴 $script: DETENIDO"
            fi
        done
        ;;
    *)
        echo "Uso: $0 {start|stop|status}"
        exit 1
        ;;
esac