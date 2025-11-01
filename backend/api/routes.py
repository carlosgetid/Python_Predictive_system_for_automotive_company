import logging
import pandas as pd
from flask import Blueprint, request, jsonify
import datetime 
import os # Importar os para la lógica de lectura de Excel

# Importar lógica (asegúrate que las rutas relativas sean correctas)
from backend.database.db_utils import get_db_engine, save_dataframe_to_db

# --- INICIO DE MODIFICACIÓN (Importar predict y training) ---
# Importamos la lógica de predicción (que carga los modelos al inicio)
import backend.ml_core.predict as predictor
# Importamos la lógica de entrenamiento como un módulo
import backend.ml_core.training as training_pipeline
# --- FIN DE MODIFICACIÓN ---


# Blueprint
api_bp = Blueprint('api', __name__)

# --- Endpoint /upload (Mejorado para leer hoja 'Detalle') ---
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Recibe CSV/Excel. Si es Excel, lee la hoja 'Detalle'.
    Extrae SKU, Fecha Venta, Cantidad -> id_producto, fecha, cantidad_vendida.
    Valida y guarda en 'ventas_historicas'.
    """
    try:
        if 'file' not in request.files:
            logging.warning("Intento de subida sin archivo.")
            return jsonify({"error": "No se encontró el archivo"}), 400

        file = request.files['file']
        df = None
        required_cols_raw = set() # Inicializar
        rename_map = {} # Inicializar

        # --- Lectura y Validación de Formato ---
        try:
            if file.filename.endswith('.csv'):
                # Si es CSV, asumimos que ya tiene las columnas correctas
                df = pd.read_csv(file)
                # Nombres esperados para CSV pre-procesado
                required_cols_raw = {'id_producto', 'fecha', 'cantidad_vendida'}
                rename_map = {} # No necesita renombrar

            elif file.filename.endswith(('.xls', '.xlsx')):
                # Si es Excel, leer la hoja 'Detalle'
                # Asegúrate que 'openpyxl' esté en requirements.txt
                try:
                    df = pd.read_excel(file, sheet_name='Detalle', engine='openpyxl')
                    logging.info(f"Leída hoja 'Detalle' del archivo Excel '{file.filename}'.")
                except ValueError as sheet_error:
                    # Captura error si la hoja 'Detalle' no se encuentra
                    logging.error(f"Error al leer hoja 'Detalle' de '{file.filename}': {sheet_error}")
                    return jsonify({"error": "El archivo Excel no contiene una hoja llamada 'Detalle'."}), 400
                except Exception as excel_read_error:
                     # Captura otros errores de lectura de Excel (ej. archivo corrupto)
                    logging.error(f"Error general al leer Excel '{file.filename}': {excel_read_error}", exc_info=True)
                    return jsonify({"error": f"Error al leer el archivo Excel: {excel_read_error}"}), 400

                # Nombres esperados en la hoja 'Detalle'
                required_cols_raw = {'SKU', 'Fecha Venta', 'Cantidad'}
                # Mapa para renombrar las columnas
                rename_map = {
                    'SKU': 'id_producto',
                    'Fecha Venta': 'fecha',
                    'Cantidad': 'cantidad_vendida'
                }

            else:
                return jsonify({"error": "Formato de archivo no soportado (solo .csv, .xls, .xlsx)"}), 400

        except Exception as e:
            logging.error(f"Error al intentar leer el archivo '{file.filename}': {e}", exc_info=True)
            return jsonify({"error": f"Error general al leer el archivo: {e}"}), 400

        # Verificar si la lectura fue exitosa
        if df is None:
             logging.error("DataFrame quedó como None después de intentar leer el archivo.")
             return jsonify({"error": "No se pudo leer el archivo correctamente."}), 400
        if df.empty:
             logging.warning(f"El archivo '{file.filename}' (o la hoja 'Detalle') está vacío.")
             return jsonify({"error": "El archivo o la hoja 'Detalle' está vacía."}), 400


        # --- Validación de Columnas (Adaptada) ---
        actual_cols = set(df.columns)
        if not required_cols_raw.issubset(actual_cols):
            missing = required_cols_raw - actual_cols
            expected_str = "'SKU', 'Fecha Venta', 'Cantidad'" if rename_map else "'id_producto', 'fecha', 'cantidad_vendida'"
            logging.warning(f"Archivo '{file.filename}' rechazado. Faltan columnas {expected_str}: {missing}")
            return jsonify({"error": f"Faltan columnas obligatorias ({expected_str}): {missing}"}), 400

        # --- Selección y Renombrado ---
        logging.info(f"Columnas encontradas: {list(actual_cols)}. Columnas requeridas: {list(required_cols_raw)}")
        # Seleccionar solo las columnas necesarias ANTES de renombrar
        df_selected = df[list(required_cols_raw)].copy()
        # Renombrar si es necesario (si era Excel)
        if rename_map:
            df_selected.rename(columns=rename_map, inplace=True)
            logging.info(f"Columnas renombradas a: {list(df_selected.columns)}")

        df_to_save = df_selected

        # --- Limpieza y Formateo (Misma lógica de antes) ---
        logging.info("Iniciando limpieza y formateo de datos...")
        try:
            df_to_save['fecha'] = pd.to_datetime(df_to_save['fecha'], errors='coerce')
            rows_before = len(df_to_save)
            df_to_save.dropna(subset=['fecha'], inplace=True)
            dropped_rows = rows_before - len(df_to_save)
            if dropped_rows > 0:
                logging.warning(f"Se eliminaron {dropped_rows} filas por formato de fecha inválido.")

            df_to_save['cantidad_vendida'] = pd.to_numeric(df_to_save['cantidad_vendida'], errors='coerce')
            df_to_save.dropna(subset=['cantidad_vendida'], inplace=True) # Eliminar nulos de cantidad
            df_to_save['cantidad_vendida'] = df_to_save['cantidad_vendida'].astype(int)
            df_to_save = df_to_save[df_to_save['cantidad_vendida'] > 0] # Mantener solo > 0
            df_to_save['id_producto'] = df_to_save['id_producto'].astype(str)

        except Exception as e:
             logging.error(f"Error inesperado durante la limpieza de datos: {e}", exc_info=True)
             return jsonify({"error": f"Error procesando los datos extraídos: {e}"}), 400

        if df_to_save.empty:
            logging.warning("No quedan datos válidos después de la limpieza completa (ej. fechas inválidas o cantidad <= 0).")
            return jsonify({"error": "No se encontraron datos válidos (SKU, Fecha Venta válida, Cantidad > 0) en el archivo/hoja."}), 400
        
        logging.info(f"Limpieza completada. {len(df_to_save)} filas válidas listas para guardar.")

        # --- Guardado en BD ---
        engine = get_db_engine()
        if engine is None:
            logging.error("Fallo al obtener conexión a BD en /upload.")
            return jsonify({"error": "Error interno del servidor (BD)"}), 500

        success, message = save_dataframe_to_db(df_to_save, "ventas_historicas", engine)

        if success:
            summary = {
                "archivo_recibido": file.filename,
                "filas_leidas_hoja_detalle_o_csv": len(df),
                "filas_validas_guardadas": len(df_to_save)
            }
            logging.info(f"Datos guardados con éxito. Resumen: {summary}")
            return jsonify({"message": message, "data_summary": summary}), 201
        else:
            logging.error(f"Fallo al guardar en BD: {message}")
            return jsonify({"error": message}), 500

    except Exception as e:
        logging.error(f"[ERROR /upload Mejorado - General] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno inesperado en el servidor: {e}"}), 500


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

