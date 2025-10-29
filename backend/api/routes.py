import logging
import pandas as pd
from flask import Blueprint, request, jsonify
import datetime # Necesario para isinstance check

# Importar lógica (asegúrate que las rutas relativas sean correctas)
from backend.database.db_utils import get_db_engine, save_dataframe_to_db
from backend.ml_core.predict import make_single_prediction

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
                # Usar try-except por si la hoja no existe
                try:
                    df = pd.read_excel(file, sheet_name='Detalle', engine='openpyxl')
                except ValueError as sheet_error:
                    # Captura error si la hoja 'Detalle' no se encuentra
                    logging.error(f"Error al leer hoja 'Detalle' de '{file.filename}': {sheet_error}")
                    return jsonify({"error": "El archivo Excel no contiene una hoja llamada 'Detalle'."}), 400

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
            logging.error(f"Error al leer el archivo '{file.filename}': {e}", exc_info=True)
            return jsonify({"error": f"Error general al leer el archivo: {e}"}), 400

        # Verificar si la lectura fue exitosa
        if df is None:
             return jsonify({"error": "No se pudo leer el archivo correctamente."}), 400


        # --- Validación de Columnas (Adaptada) ---
        actual_cols = set(df.columns)
        if not required_cols_raw.issubset(actual_cols):
            missing = required_cols_raw - actual_cols
            expected = "'SKU', 'Fecha Venta', 'Cantidad'" if rename_map else "'id_producto', 'fecha', 'cantidad_vendida'"
            logging.warning(f"Archivo '{file.filename}' rechazado. Faltan columnas {expected}: {missing}")
            return jsonify({"error": f"Faltan columnas obligatorias ({expected}): {missing}"}), 400

        # --- Selección y Renombrado ---
        # Seleccionar solo las columnas necesarias ANTES de renombrar
        df_selected = df[list(required_cols_raw)].copy()
        # Renombrar si es necesario (si era Excel)
        if rename_map:
            df_selected.rename(columns=rename_map, inplace=True)

        # Ahora df_selected tiene las columnas 'id_producto', 'fecha', 'cantidad_vendida'
        df_to_save = df_selected

        # --- Limpieza y Formateo (Misma lógica de antes) ---
        try:
            df_to_save['fecha'] = pd.to_datetime(df_to_save['fecha'], errors='coerce')
            rows_before = len(df_to_save)
            df_to_save.dropna(subset=['fecha'], inplace=True)
            if len(df_to_save) < rows_before:
                logging.warning(f"Se eliminaron {rows_before - len(df_to_save)} filas por formato de fecha inválido.")
        except Exception as e:
             logging.error(f"Error inesperado convirtiendo 'fecha': {e}", exc_info=True)
             return jsonify({"error": f"Error procesando la columna 'fecha': {e}"}), 400

        df_to_save['cantidad_vendida'] = pd.to_numeric(df_to_save['cantidad_vendida'], errors='coerce')
        df_to_save['cantidad_vendida'] = df_to_save['cantidad_vendida'].fillna(0).astype(int)
        df_to_save = df_to_save[df_to_save['cantidad_vendida'] > 0]

        if df_to_save.empty:
            return jsonify({"error": "No quedan datos válidos después de la limpieza."}), 400

        df_to_save['id_producto'] = df_to_save['id_producto'].astype(str)

        # --- Guardado en BD ---
        engine = get_db_engine()
        if engine is None:
            logging.error("Fallo al obtener conexión a BD en /upload.")
            return jsonify({"error": "Error interno del servidor (BD)"}), 500

        success, message = save_dataframe_to_db(df_to_save, "ventas_historicas", engine)

        if success:
            summary = {
                "filas_recibidas_hoja_detalle": len(df), # Filas leídas de 'Detalle' o CSV
                "filas_validas_guardadas": len(df_to_save)
            }
            return jsonify({"message": message, "data_summary": summary}), 201
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        logging.error(f"[ERROR /upload Mejorado] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno inesperado: {e}"}), 500


# --- Endpoint /predict (Revertido a MVP) ---
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

        # Llamar a la lógica de ML (predict.py)
        prediccion = make_single_prediction(id_producto, fecha_str)

        if prediccion is None:
            # make_single_prediction devuelve None si el producto es desconocido o hay error
            logging.warning(f"Predicción fallida para {id_producto} en {fecha_str}")
            # Devolver 404 si el producto es desconocido, 500 si fue otro error interno
            # (Simplificamos a 404 por ahora, predict.py ya logueó la razón)
            return jsonify({"error": f"No se pudo generar predicción para '{id_producto}'. Verifique el ID o la fecha."}), 404
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
        # Asegurarse que la columna 'fecha' exista
        if 'fecha' in df_hist.columns:
            # Formato YYYY-MM-DD es estándar y bueno para JSON/JS
             df_hist['fecha'] = pd.to_datetime(df_hist['fecha']).dt.strftime('%Y-%m-%d')
        else:
            logging.warning(f"La consulta de historial para '{id_producto}' no devolvió la columna 'fecha'.")
            # Devolver un error o un historial vacío, dependiendo del caso esperado
            return jsonify({"historial": []}), 200 # Opcional: devolver 200 con lista vacía si la falta de fecha no es crítica

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

