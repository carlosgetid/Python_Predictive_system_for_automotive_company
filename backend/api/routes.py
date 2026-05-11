import logging
import pandas as pd
import shutil  # <--- AGREGAR ESTA LÍNEA
from flask import Blueprint, request, jsonify
import datetime 
import os
import subprocess
import signal

# Importar lógica BD
from backend.database.db_utils import get_db_engine, save_dataframe_to_db, get_model_metrics_history, get_active_alerts, update_alert_status, get_db_engine_and_init, get_config_params, update_config_params, reset_db_tables, get_all_users, update_user_email, get_pipeline_interval, set_pipeline_interval
from backend.services.ingestion_service import ingest_dataframe_to_db, process_excel_file_from_disk
# --- INICIO DE AGREGADO ---
# Importamos el Servicio de Ingesta (HU-010) y alertas (HU-007)
from backend.services.auth_service import authenticate_user
from backend.services.alert_service import run_daily_alert_analysis
from backend.services.email_service import send_alerts_summary
import threading
import jwt
from functools import wraps
from pydantic import ValidationError
from backend.api.schemas import AlertConfigCreate
from backend.database.db_utils import get_alert_configs, upsert_alert_config

SECRET_KEY = "tu_clave_secreta_super_segura" # Para MVP

def require_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            if 'Authorization' in request.headers:
                parts = request.headers['Authorization'].split()
                if len(parts) == 2 and parts[0] == 'Bearer':
                    token = parts[1]
            if not token:
                return jsonify({"error": "Token faltante o inválido"}), 401
            try:
                data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                if data['rol'] not in roles:
                    return jsonify({"error": "No tienes permisos para realizar esta acción"}), 403
                request.user = data
            except Exception as e:
                return jsonify({"error": f"Token inválido: {e}"}), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator
# --- FIN DE AGREGADO ---

# Importamos la lógica de predicción...
import backend.ml_core.predict as predictor
import backend.ml_core.training as training_pipeline


# Blueprint
api_bp = Blueprint('api', __name__)

# --- INICIO DE AGREGADO: Configuración Ingesta Automática ---
BASE_DATA_DIR = "data_fuente"
INGEST_DIR = os.path.join(BASE_DATA_DIR, "entrada")
PROCESSED_DIR = os.path.join(BASE_DATA_DIR, "procesados")
FAILED_DIR = os.path.join(BASE_DATA_DIR, "fallidos")

# Asegurar existencia de directorios
for d in [INGEST_DIR, PROCESSED_DIR, FAILED_DIR]:
    os.makedirs(d, exist_ok=True)
# --- FIN DE AGREGADO ---

# --- Endpoint /upload (Refactorizado para usar Servicio Centralizado) ---
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Recibe CSV/Excel. Lee el archivo (mantiene lógica de lectura existente).
    Delega la Validación, Limpieza y Guardado al servicio 'ingest_dataframe_to_db'.
    """
    try:
        if 'file' not in request.files:
            logging.warning("Intento de subida sin archivo.")
            return jsonify({"error": "No se encontró el archivo"}), 400

        file = request.files['file']
        if file.filename == '':
             return jsonify({"error": "Nombre de archivo vacío"}), 400

        df = None
        
        # --- BLOQUE 1: Lectura (MANTENIENDO TU LÓGICA DE LECTURA ROBUSTA) ---
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xls', '.xlsx')):
                try:
                    # Mantenemos tu validación específica de hoja 'Detalle'
                    df = pd.read_excel(file, sheet_name='Detalle', engine='openpyxl')
                    logging.info(f"Leída hoja 'Detalle' del archivo Excel '{file.filename}'.")
                except ValueError as sheet_error:
                    logging.error(f"Error al leer hoja 'Detalle' de '{file.filename}': {sheet_error}")
                    return jsonify({"error": "El archivo Excel no contiene una hoja llamada 'Detalle'."}), 400
                except Exception as excel_read_error:
                    logging.error(f"Error general al leer Excel '{file.filename}': {excel_read_error}", exc_info=True)
                    return jsonify({"error": f"Error al leer el archivo Excel: {excel_read_error}"}), 400
            else:
                return jsonify({"error": "Formato de archivo no soportado (solo .csv, .xls, .xlsx)"}), 400

        except Exception as e:
            logging.error(f"Error al intentar leer el archivo '{file.filename}': {e}", exc_info=True)
            return jsonify({"error": f"Error general al leer el archivo: {e}"}), 400

        # Verificar si la lectura fue exitosa (Tu lógica original)
        if df is None:
             logging.error("DataFrame quedó como None después de intentar leer el archivo.")
             return jsonify({"error": "No se pudo leer el archivo correctamente."}), 400
        if df.empty:
             logging.warning(f"El archivo '{file.filename}' (o la hoja 'Detalle') está vacío.")
             return jsonify({"error": "El archivo o la hoja 'Detalle' está vacía."}), 400

        # --- BLOQUE 2: Procesamiento y Guardado (REFACTORIZADO) ---
        # AQUI ESTA EL CAMBIO: En lugar de tener 50 líneas para limpiar y guardar,
        # llamamos a esta función que hace validación, limpieza Y GUARDADO (save_dataframe_to_db) internamente.
        
        success, message, rows_saved = ingest_dataframe_to_db(df, f"Manual_{file.filename}")

        if success:
            summary = {
                "archivo_recibido": file.filename,
                "filas_leidas_originales": len(df),
                "filas_validas_guardadas": rows_saved
            }
            logging.info(f"Datos guardados con éxito. Resumen: {summary}")
            return jsonify({"message": message, "data_summary": summary}), 201
        else:
            # El servicio devuelve el mensaje de error específico (ej. "Fallo al guardar en BD")
            logging.error(f"Fallo en el procesamiento del servicio: {message}")
            return jsonify({"error": message}), 400

    except Exception as e:
        logging.error(f"[ERROR CRITICO /upload] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno inesperado en el servidor: {e}"}), 500

# --- INICIO DE AGREGADO: Endpoint Ingesta Automatizada HU-010 ---
@api_bp.route('/api/v1/trigger_ingestion', methods=['POST'])
def trigger_ingestion():
    """
    HU-010: Disparador de ingesta batch desde disco.
    Escanea '/data_fuente/entrada', procesa archivos y los mueve.
    """
    logging.info("--- Iniciando ciclo de Ingesta Automatizada ---")
    report = {"processed": [], "failed": [], "total_found": 0}

    try:
        # 1. Escaneo
        if not os.path.exists(INGEST_DIR):
             return jsonify({"error": f"Directorio no encontrado: {INGEST_DIR}"}), 500
             
        files = [f for f in os.listdir(INGEST_DIR) if f.endswith(('.xlsx', '.xls'))]
        report["total_found"] = len(files)

        if not files:
            return jsonify({"message": "No hay archivos pendientes.", "report": report}), 200

        # 2. Procesamiento Batch
        for filename in files:
            src_path = os.path.join(INGEST_DIR, filename)
            
            # Llamada al servicio específico para archivos en disco
            success = process_excel_file_from_disk(src_path)

            # 3. Gestión de Archivos (Mover a procesados/fallidos)
            try:
                if success:
                    dst_path = os.path.join(PROCESSED_DIR, filename)
                    shutil.move(src_path, dst_path)
                    report["processed"].append(filename)
                    logging.info(f"ARCHIVO PROCESADO: {filename}")
                else:
                    dst_path = os.path.join(FAILED_DIR, filename)
                    shutil.move(src_path, dst_path)
                    report["failed"].append(filename)
                    logging.warning(f"ARCHIVO FALLIDO: {filename}")
            except OSError as io_err:
                logging.error(f"Error de sistema moviendo archivo {filename}: {io_err}")
                report["failed"].append(f"{filename} (Error IO)")

        # Respuesta Parcial (207) o Exitosa (200)
        status_code = 200 if not report["failed"] else 207
        return jsonify({"message": "Ciclo de ingesta finalizado.", "report": report}), status_code

    except Exception as e:
        logging.error(f"Error crítico en trigger_ingestion: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
# --- FIN DE AGREGADO ---

# --- Endpoint /predict (ACTUALIZADO para usar el predictor importado) ---
@api_bp.route('/predict', methods=['POST'])
def predict():
    """
    Recibe id_producto y fecha_str, devuelve predicción de cantidad (MVP).
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON vacío"}), 400

        id_producto = data.get('id_producto')
        fecha_str = data.get('fecha_str')

        if not id_producto or not fecha_str:
            return jsonify({"error": "Faltan 'id_producto' o 'fecha_str'"}), 400

        # --- CAMBIO CLAVE ---
        # Llamar a la lógica de ML usando el módulo 'predictor' importado
        # La función make_single_prediction ahora viene de 'predictor'
        prediccion = predictor.make_single_prediction(id_producto, fecha_str)

        if prediccion is None:
            # make_single_prediction devuelve None si el producto es desconocido o hay error
            logging.warning(f"Predicción fallida para {id_producto} en {fecha_str}")
            # Devolver 404 si el producto es desconocido
            return jsonify({"error": f"No se pudo generar predicción para '{id_producto}'. Verifique el ID o la fecha, o si el producto es nuevo."}), 404
        else:
            # ¡Éxito!
            return jsonify({"prediccion": prediccion}), 200

    except Exception as e:
        logging.error(f"[ERROR /predict MVP] {e}", exc_info=True)
        return jsonify({"error": f"Error interno en la predicción: {e}"}), 500


# --- Endpoint /history (Revertido a MVP y CORREGIDO) ---
@api_bp.route('/history', methods=['POST'])
def get_history():
    """
    Recibe id_producto, devuelve historial de cantidad_vendida (MVP).
    CORREGIDO para manejar fechas correctamente.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON vacío"}), 400

        id_producto = data.get('id_producto')
        if not id_producto:
            return jsonify({"error": "Falta 'id_producto'"}), 400

        engine = get_db_engine()
        if engine is None:
            logging.error("Fallo al obtener conexión a BD en /history.")
            return jsonify({"error": "Error interno del servidor (BD)"}), 500

        # Consulta segura
        # <-- CAMBIO: Nombre de tabla actualizado a 'ventas_detalle'
        query = "SELECT fecha, cantidad_vendida FROM ventas_detalle WHERE id_producto = %s ORDER BY fecha ASC"

        # Usar try-except específico para la consulta
        try:
            df_hist = pd.read_sql(
                query,
                con=engine,
                params=(str(id_producto),) # Asegurar que es string para el parámetro
            )
        except Exception as db_err:
             logging.error(f"Error al ejecutar consulta de historial para '{id_producto}': {db_err}", exc_info=True)
             return jsonify({"error": f"Error consultando la base de datos: {db_err}"}), 500


        # --- CORRECCIÓN CLAVE ---
        # Convertir la columna 'fecha' a string ANTES de convertir a dict
        if 'fecha' in df_hist.columns:
            # Formato YYYY-MM-DD es estándar y bueno para JSON/JS
             df_hist['fecha'] = pd.to_datetime(df_hist['fecha']).dt.strftime('%Y-%m-%d')
        else:
            logging.warning(f"La consulta de historial para '{id_producto}' no devolvió la columna 'fecha'.")
            return jsonify({"historial": []}), 200 

        # Asegurar que cantidad_vendida sea numérica (int)
        if 'cantidad_vendida' in df_hist.columns:
             df_hist['cantidad_vendida'] = pd.to_numeric(df_hist['cantidad_vendida'], errors='coerce').fillna(0).astype(int)

        # Convertir a lista de diccionarios (JSON serializable)
        historial = df_hist.to_dict('records')

        return jsonify({"historial": historial}), 200

    except Exception as e:
        # Captura general por si algo más falla
        logging.error(f"[ERROR /history MVP] {e}", exc_info=True)
        return jsonify({"error": f"Error interno obteniendo historial: {e}"}), 500

# --- Endpoint de Health Check (opcional pero útil) ---
@api_bp.route('/health')
def health_check():
    """Verifica si el servidor está vivo."""
    return {"status": "ok"}, 200


# --- INICIO DE NUEVO CÓDIGO (ENDPOINT DE RE-ENTRENAMIENTO) ---
@api_bp.route('/api/v1/trigger_retraining', methods=['POST'])
def trigger_retraining():
    """
    Endpoint protegido (por la UI) para disparar el re-entrenamiento
    y la recarga de modelos en vivo.
    """
    logging.info("Solicitud de re-entrenamiento recibida por la API...")
    
    try:
        # 1. Ejecutar el pipeline de entrenamiento
        # (Llama a la función 'train_and_evaluate' de training.py)
        # Esta función ahora devuelve un diccionario con estado y métricas.
        training_results = training_pipeline.train_and_evaluate()
        
        # Verificar si el entrenamiento falló
        if not training_results or training_results.get("status") != "success":
            error_msg = training_results.get("message", "Error desconocido durante el entrenamiento.")
            logging.error(f"El pipeline de entrenamiento falló: {error_msg}")
            return jsonify({"error": "Falló el pipeline de entrenamiento.", "details": error_msg}), 500

        # 2. Recargar los modelos en la memoria de 'predict.py'
        # (Llama a la función 'reload_artifacts' de predict.py)
        logging.info("Entrenamiento completado. Recargando modelos en vivo...")
        reload_success = predictor.reload_artifacts() # ¡Llamada clave!
        
        if not reload_success:
            # Esto es un estado crítico: el entrenamiento funcionó pero el servidor
            # sigue usando los modelos antiguos.
            logging.error("¡FALLO CRÍTICO! Entrenamiento exitoso, pero no se pudieron recargar los nuevos modelos en vivo.")
            return jsonify({
                "error": "Entrenamiento exitoso, pero la recarga de modelos falló. Se requiere reinicio manual del servidor backend.",
                "metrics": training_results.get("metrics", {})
            }), 500
        
        logging.info("Modelos recargados en vivo con éxito.")
        
        # 3. Devolver éxito y métricas al frontend
        return jsonify({
            "message": "Re-entrenamiento completado y modelos recargados en vivo con éxito.",
            "metrics": training_results.get("metrics", {}),
            "save_status": training_results.get("save_status", [])
        }), 200

    except Exception as e:
        # Captura de error general para el endpoint
        logging.error(f"Error inesperado durante /trigger_retraining: {e}", exc_info=True)
        return jsonify({"error": f"Error interno del servidor durante el re-entrenamiento: {str(e)}"}), 500

# --- Endpoint 7: Obtener Historial de Métricas (HU-011) ---
@api_bp.route('/api/v1/metrics', methods=['GET'])
def get_metrics_history():
    """
    Devuelve el historial de métricas de rendimiento de los modelos
    almacenado en la base de datos (tabla model_metrics).
    """
    try:
        engine = get_db_engine()
        if engine is None:
            return jsonify({"error": "Error interno: No hay conexión a BD"}), 500

        # Obtener historial usando la función de utilidad
        df_metrics = get_model_metrics_history(engine)
        
        # Si está vacío, devolver lista vacía
        if df_metrics.empty:
            return jsonify({"metrics": []}), 200
            
        # Convertir a lista de diccionarios para JSON
        metrics_data = df_metrics.to_dict(orient='records')
        
        return jsonify({"metrics": metrics_data}), 200

    except Exception as e:
        logging.error(f"Error obteniendo historial de métricas: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    
# --- Endpoint Autenticación (Login) ---
@api_bp.route('/login', methods=['POST'])
def login():
    """
    Recibe credenciales JSON (username, password).
    Valida contra la BD y devuelve datos del usuario si es correcto.
    """
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Faltan credenciales"}), 400

        user = authenticate_user(data['username'], data['password'])

        if user:
            # Generate JWT
            token = jwt.encode({
                'id': user['id'],
                'username': user['username'],
                'rol': user['rol'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, SECRET_KEY, algorithm="HS256")
            
            # Login Exitoso
            return jsonify({
                "message": "Login exitoso",
                "user": user,
                "token": token
            }), 200
        else:
            # Login Fallido
            return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    except Exception as e:
        logging.error(f"Error en /login: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor"}), 500

# --- INICIO DE AGREGADO: Alertas (HU-007) ---
@api_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Retorna la lista de alertas pendientes."""
    try:
        engine = get_db_engine_and_init()
        if not engine:
            return jsonify({"error": "Error de conexión a BD"}), 500
            
        alerts = get_active_alerts(engine)
        return jsonify(alerts), 200
    except Exception as e:
        logging.error(f"Error en GET /api/alerts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/alerts/<alert_id>/status', methods=['PUT'])
def update_alert(alert_id):
    """Actualiza el estado de una alerta."""
    try:
        data = request.get_json()
        if not data or 'estado' not in data:
            return jsonify({"error": "Falta el campo 'estado'"}), 400
            
        nuevo_estado = data['estado']
        engine = get_db_engine()
        
        success = update_alert_status(alert_id, nuevo_estado, engine)
        if success:
            return jsonify({"message": f"Alerta actualizada a {nuevo_estado}"}), 200
        else:
            return jsonify({"error": "No se pudo actualizar la alerta (no encontrada o estado inválido)"}), 400
            
    except Exception as e:
        logging.error(f"Error en PUT /api/alerts/<id>/status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/jobs/generate-alerts', methods=['POST'])
def trigger_generate_alerts():
    """Gatilla el análisis diario de alertas en background."""
    try:
        # Asegurar inicialización de la tabla antes del hilo
        get_db_engine_and_init()
        
        # Ejecutar en thread para retornar 202 rápido
        thread = threading.Thread(target=run_daily_alert_analysis)
        thread.start()
        
        return jsonify({"message": "Job de alertas iniciado en background"}), 202
    except Exception as e:
        logging.error(f"Error en POST /api/jobs/generate-alerts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# --- INICIO DE AGREGADO: Configuración de Sistema ---
@api_bp.route('/api/config', methods=['GET'])
def get_config():
    """Retorna la configuración actual del sistema."""
    try:
        engine = get_db_engine_and_init()
        if not engine:
            return jsonify({"error": "Error de conexión a BD"}), 500
        config = get_config_params(engine)
        return jsonify(config), 200
    except Exception as e:
        logging.error(f"Error en GET /api/config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/config', methods=['POST'])
def update_config():
    """Actualiza la configuración del sistema."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        
        engine = get_db_engine_and_init()
        success = update_config_params(data, engine)
        if success:
            return jsonify({"message": "Configuración actualizada correctamente"}), 200
        else:
            return jsonify({"error": "No se pudo actualizar la configuración"}), 500
    except Exception as e:
        logging.error(f"Error en POST /api/config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/config/test-email', methods=['POST'])
def test_email():
    """Envía un correo de prueba usando la configuración actual."""
    try:
        # 1. Obtener la configuración más reciente
        config = get_config_params()
        destinatario = config.get("email_destinatario_alertas")
        perfil = config.get("perfil_destinatario_alertas", "Desconocido")
        
        if not destinatario:
            return jsonify({"error": "No hay destinatario configurado"}), 400

        # 2. Generar alerta de prueba
        test_alert = [{
            "sku": "TEST-001",
            "tipo": "PRUEBA",
            "mensaje": "Este es un correo de prueba de configuración.",
            "fecha_proyeccion": datetime.date.today().strftime("%Y-%m-%d")
        }]

        # 3. Intentar enviar
        success = send_alerts_summary(test_alert, recipient_email=destinatario)
        if success:
            return jsonify({
                "message": f"Correo de prueba enviado al perfil: {perfil}", 
                "status": "success"
            }), 200
        else:
            return jsonify({"error": "Falló el envío. Verifica las credenciales y el puerto SMTP en los logs del servidor."}), 500
    except Exception as e:
        logging.error(f"Error en POST /api/config/test-email: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# --- INICIO DE AGREGADO: Configuración de Alertas (HU-012) ---
@api_bp.route('/api/v1/alerts/config', methods=['GET'])
def get_alert_config_endpoint():
    """Obtiene las configuraciones de alertas."""
    try:
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 100))
        engine = get_db_engine()
        configs = get_alert_configs(engine, skip, limit)
        return jsonify(configs), 200
    except Exception as e:
        logging.error(f"Error en GET /api/v1/alerts/config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v1/alerts/config', methods=['POST'])
@require_role(["Gerente Administración", "Gerente General", "Jefa Almacén", "Analista Logística"])
def upsert_alert_config_endpoint():
    """Crea o actualiza la configuración de alerta para un producto."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validar con Pydantic
        config_schema = AlertConfigCreate(**data)
        
        # Enriquecer con usuario que actualiza
        config_dict = config_schema.model_dump()
        config_dict['updated_by'] = request.user.get('username', 'Sistema')
        
        engine = get_db_engine()
        success = upsert_alert_config(engine, config_dict)
        if success:
            return jsonify({"message": "Configuración de alerta actualizada exitosamente"}), 200
        else:
            return jsonify({"error": "Error interno al actualizar la configuración"}), 500
            
    except ValidationError as e:
        return jsonify({"error": "Error de validación", "details": e.errors()}), 400
    except Exception as e:
        logging.error(f"Error en POST /api/v1/alerts/config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v1/reset-db', methods=['POST'])
def reset_db_endpoint():
    """Limpia las tablas de datos (ventas_detalle y entrenamiento)"""
    try:
        success, message = reset_db_tables()
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 500
    except Exception as e:
        logging.error(f"Error en POST /api/v1/reset-db: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v1/users', methods=['GET'])
def get_users_endpoint():
    try:
        users = get_all_users()
        return jsonify(users), 200
    except Exception as e:
        logging.error(f"Error en GET /api/v1/users: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v1/users/<int:user_id>/email', methods=['PUT'])
def update_email_endpoint(user_id):
    try:
        data = request.json
        new_email = data.get('correo_electronico')
        if not new_email:
            return jsonify({"error": "correo_electronico es requerido"}), 400
            
        success = update_user_email(user_id, new_email)
        if success:
            return jsonify({"message": "Correo actualizado"}), 200
        else:
            return jsonify({"error": "No se pudo actualizar el correo"}), 500
    except Exception as e:
        logging.error(f"Error en PUT /api/v1/users/{user_id}/email: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================
# PIPELINE MANAGER — Control de Workers desde la UI
# ============================================================

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
SCRIPTS_DIR = os.path.normpath(SCRIPTS_DIR)

WORKERS = [
    {"id": "worker_ingestion",   "script": "worker_ingestion.sh",   "label": "Ingesta de Datos",    "log": "ingestion.log",   "default_interval": 30},
    {"id": "worker_retraining",  "script": "worker_retraining.sh",  "label": "Reentrenamiento ML",  "log": "retraining.log",  "default_interval": 60},
    {"id": "worker_metrics",     "script": "worker_metrics.sh",     "label": "Métricas",            "log": "metrics.log",    "default_interval": 300},
    {"id": "worker_alerts",      "script": "worker_alerts.sh",      "label": "Alertas",             "log": "alerts.log",     "default_interval": 180},
]

def _get_pid_file(worker_id):
    return os.path.join(SCRIPTS_DIR, "pids", f"{worker_id}.sh.pid")

def _is_running(worker_id):
    pid_file = _get_pid_file(worker_id)
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Signal 0: solo verifica si el proceso existe
        return True
    except (ProcessLookupError, ValueError, OSError):
        # El proceso no existe, limpiar el archivo PID stale
        try:
            os.remove(pid_file)
        except Exception:
            pass
        return False

def _get_pid(worker_id):
    pid_file = _get_pid_file(worker_id)
    try:
        with open(pid_file) as f:
            return int(f.read().strip())
    except Exception:
        return None


@api_bp.route('/api/v1/pipeline/status', methods=['GET'])
def pipeline_status():
    """Retorna el estado de todos los workers del pipeline."""
    result = []
    for w in WORKERS:
        running = _is_running(w["id"])
        pid = _get_pid(w["id"]) if running else None
        result.append({
            "id": w["id"],
            "label": w["label"],
            "script": w["script"],
            "running": running,
            "pid": pid,
            "log": w["log"],
            "default_interval": w["default_interval"]
        })
    return jsonify(result), 200


@api_bp.route('/api/v1/pipeline/<worker_id>/start', methods=['POST'])
def pipeline_start_worker(worker_id):
    """Inicia un worker específico usando nohup (persiste más allá del proceso padre)."""
    worker = next((w for w in WORKERS if w["id"] == worker_id), None)
    if not worker:
        return jsonify({"error": f"Worker '{worker_id}' no encontrado"}), 404

    if _is_running(worker_id):
        pid = _get_pid(worker_id)
        return jsonify({"message": f"Worker ya está corriendo", "pid": pid}), 200

    try:
        script_path = os.path.join(SCRIPTS_DIR, worker["script"])
        pid_file = _get_pid_file(worker_id)
        log_file = os.path.join(SCRIPTS_DIR, "logs", worker["log"])

        # Asegurar que el script sea ejecutable
        os.chmod(script_path, 0o755)
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Iniciar con nohup para que sobreviva el proceso padre
        process = subprocess.Popen(
            ["bash", script_path],
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,  # Nuevo grupo de procesos (sobrevive recargas)
            close_fds=True
        )

        with open(pid_file, 'w') as f:
            f.write(str(process.pid))

        logging.info(f"Pipeline: Worker '{worker_id}' iniciado con PID {process.pid}")
        worker_label = worker['label']
        return jsonify({"message": f"Worker '{worker_label}' iniciado", "pid": process.pid}), 200

    except Exception as e:
        logging.error(f"Error iniciando worker '{worker_id}': {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_bp.route('/api/v1/pipeline/<worker_id>/stop', methods=['POST'])
def pipeline_stop_worker(worker_id):
    """Detiene un worker específico enviando SIGTERM al grupo de procesos."""
    worker = next((w for w in WORKERS if w["id"] == worker_id), None)
    if not worker:
        return jsonify({"error": f"Worker '{worker_id}' no encontrado"}), 404

    if not _is_running(worker_id):
        return jsonify({"message": "Worker ya estaba detenido"}), 200

    try:
        pid = _get_pid(worker_id)
        pid_file = _get_pid_file(worker_id)

        # Terminar el grupo de procesos completo
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass  # Ya terminó

        # Limpiar el archivo PID
        if os.path.exists(pid_file):
            os.remove(pid_file)

        logging.info(f"Pipeline: Worker '{worker_id}' (PID {pid}) detenido")
        worker_label = worker['label']
        return jsonify({"message": f"Worker '{worker_label}' detenido", "pid": pid}), 200

    except Exception as e:
        logging.error(f"Error deteniendo worker '{worker_id}': {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_bp.route('/api/v1/pipeline/<worker_id>/logs', methods=['GET'])
def pipeline_get_logs(worker_id):
    """Retorna las últimas N líneas del log de un worker."""
    worker = next((w for w in WORKERS if w["id"] == worker_id), None)
    if not worker:
        return jsonify({"error": f"Worker '{worker_id}' no encontrado"}), 404

    lines = int(request.args.get('lines', 50))
    log_file = os.path.join(SCRIPTS_DIR, "logs", worker["log"])

    if not os.path.exists(log_file):
        return jsonify({"logs": [], "worker": worker_id}), 200

    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        last_lines = [l.rstrip('\n') for l in all_lines[-lines:]]
        return jsonify({"logs": last_lines, "worker": worker_id, "total_lines": len(all_lines)}), 200
    except Exception as e:
        logging.error(f"Error leyendo logs de '{worker_id}': {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_bp.route('/api/v1/pipeline/start-all', methods=['POST'])
def pipeline_start_all():
    """Inicia todos los workers del pipeline."""
    results = []
    for w in WORKERS:
        try:
            if _is_running(w["id"]):
                results.append({"id": w["id"], "status": "already_running", "pid": _get_pid(w["id"])})
                continue

            script_path = os.path.join(SCRIPTS_DIR, w["script"])
            pid_file = _get_pid_file(w["id"])
            log_file = os.path.join(SCRIPTS_DIR, "logs", w["log"])

            os.chmod(script_path, 0o755)
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            process = subprocess.Popen(
                ["bash", script_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                close_fds=True
            )
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))

            results.append({"id": w["id"], "status": "started", "pid": process.pid})
        except Exception as e:
            results.append({"id": w["id"], "status": "error", "error": str(e)})

    return jsonify({"message": "Comando ejecutado", "results": results}), 200


@api_bp.route('/api/v1/pipeline/stop-all', methods=['POST'])
def pipeline_stop_all():
    """Detiene todos los workers del pipeline."""
    results = []
    for w in WORKERS:
        try:
            if not _is_running(w["id"]):
                results.append({"id": w["id"], "status": "already_stopped"})
                continue

            pid = _get_pid(w["id"])
            pid_file = _get_pid_file(w["id"])

            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass

            if os.path.exists(pid_file):
                os.remove(pid_file)

            results.append({"id": w["id"], "status": "stopped", "pid": pid})
        except Exception as e:
            results.append({"id": w["id"], "status": "error", "error": str(e)})

    return jsonify({"message": "Comando ejecutado", "results": results}), 200


# ── Intervalos de ejecución ───────────────────────────────────────────────────

WORKER_DEFAULT_MINUTES = {
    "worker_ingestion":  1,
    "worker_retraining": 3,
    "worker_metrics":    5,
    "worker_alerts":     3,
}

def _get_interval_file(worker_id):
    return os.path.join(SCRIPTS_DIR, "pids", f"{worker_id}.interval")

def _read_interval_minutes(worker_id):
    """Lee el intervalo guardado (minutos). Devuelve el default si no existe."""
    path = _get_interval_file(worker_id)
    default = WORKER_DEFAULT_MINUTES.get(worker_id, 1)
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            val = int(f.read().strip())
        return val if val >= 1 else default
    except Exception:
        return default

def _write_interval_minutes(worker_id, minutes):
    """Escribe el intervalo (minutos) en el archivo de config del worker."""
    path = _get_interval_file(worker_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(str(int(minutes)))


@api_bp.route('/api/v1/pipeline/<worker_id>/interval', methods=['GET'])
def pipeline_get_interval(worker_id):
    """Retorna el intervalo de ejecución actual del worker (en minutos) desde la BD."""
    worker = next((w for w in WORKERS if w["id"] == worker_id), None)
    if not worker:
        return jsonify({"error": f"Worker '{worker_id}' no encontrado"}), 404

    minutes = get_pipeline_interval(worker_id)
    return jsonify({"worker": worker_id, "minutes": minutes}), 200


@api_bp.route('/api/v1/pipeline/<worker_id>/interval', methods=['POST'])
def pipeline_set_interval(worker_id):
    """
    Establece la frecuencia de ejecución de un worker.
    Body JSON: {"minutes": N}  (N entero >= 1)
    Persiste en la BD y sincroniza el archivo .interval para los scripts bash.
    El cambio aplica en el próximo ciclo del worker sin reiniciarlo.
    """
    worker = next((w for w in WORKERS if w["id"] == worker_id), None)
    if not worker:
        return jsonify({"error": f"Worker '{worker_id}' no encontrado"}), 404

    data = request.get_json()
    if not data or "minutes" not in data:
        return jsonify({"error": "Se requiere el campo 'minutes' en el body"}), 400

    try:
        minutes = int(data["minutes"])
    except (ValueError, TypeError):
        return jsonify({"error": "'minutes' debe ser un entero"}), 400

    if minutes < 1:
        return jsonify({"error": "'minutes' debe ser >= 1"}), 400

    try:
        # 1. Persistir en la base de datos (fuente de verdad)
        db_ok = set_pipeline_interval(worker_id, minutes)

        # 2. Sincronizar el archivo .interval para que el bash script lo lea
        #    (fallback en caso de que la BD no esté disponible al arrancar)
        try:
            _write_interval_minutes(worker_id, minutes)
        except Exception as file_err:
            logging.warning(f"No se pudo escribir archivo .interval de '{worker_id}': {file_err}")

        worker_label = worker['label']
        if db_ok:
            logging.info(f"Pipeline: Intervalo de '{worker_id}' actualizado a {minutes} min (BD + archivo)")
            return jsonify({
                "message": f"Intervalo de '{worker_label}' actualizado a {minutes} minuto(s). Aplica en el próximo ciclo.",
                "worker": worker_id,
                "minutes": minutes
            }), 200
        else:
            return jsonify({"error": "No se pudo guardar el intervalo en la base de datos"}), 500

    except Exception as e:
        logging.error(f"Error guardando intervalo de '{worker_id}': {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --- FIN DE AGREGADO ---