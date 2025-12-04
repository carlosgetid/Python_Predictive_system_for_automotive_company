import logging
import pandas as pd
import shutil  # <--- AGREGAR ESTA LÍNEA
from flask import Blueprint, request, jsonify
import datetime 
import os 

# Importar lógica BD
from backend.database.db_utils import get_db_engine, save_dataframe_to_db

# --- INICIO DE AGREGADO ---
# Importamos el Servicio de Ingesta (HU-010)
from backend.services.ingestion_service import ingest_dataframe_to_db, process_excel_file_from_disk
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
        query = "SELECT fecha, cantidad_vendida FROM ventas_historicas WHERE id_producto = %s ORDER BY fecha ASC"

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
# --- FIN DE NUEVO CÓDIGO ---

