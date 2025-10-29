import logging
import pandas as pd
from flask import Blueprint, request, jsonify

# Importar nuestras funciones de lógica
# (Asegúrate de que db_utils.py tenga 'get_db_engine' y 'save_dataframe_to_db')
from backend.database.db_utils import get_db_engine, save_dataframe_to_db
# (Asegúrate de que predict.py tenga 'make_single_prediction')
from backend.ml_core.predict import make_single_prediction

# Crear el Blueprint (nuestro contenedor de rutas)
api_bp = Blueprint('api', __name__)

# --- Endpoint 1: /upload (HU-001) ---
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Recibe un archivo (CSV/Excel) del frontend, lo valida y lo
    guarda en la base de datos.
    """
    try:
        if 'file' not in request.files:
            logging.warning("Intento de subida sin archivo.")
            return jsonify({"error": "No se encontró el archivo"}), 400

        file = request.files['file']
        
        # --- Lógica de Validación (HU-001.T4) ---
        try:
            # Determinar el tipo de archivo y leerlo
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                return jsonify({"error": "Formato de archivo no soportado"}), 400
        except Exception as e:
            logging.error(f"Error al leer el archivo: {e}")
            return jsonify({"error": f"Error al leer el archivo: {e}"}), 400

        # Validar columnas
        required_cols = {'id_producto', 'fecha', 'cantidad_vendida'}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            return jsonify({"error": f"Faltan columnas obligatorias: {missing}"}), 400

        # Seleccionar, limpiar y formatear datos
        df_to_save = df[list(required_cols)].copy()
        df_to_save['fecha'] = pd.to_datetime(df_to_save['fecha'])
        # (Aquí se podrían añadir más limpiezas, ej. eliminar nulos)

        # --- Lógica de Guardado (HU-001.T5) ---
        engine = get_db_engine()
        if engine is None:
            logging.error("No se pudo obtener el motor de la BD.")
            return jsonify({"error": "Error interno: No se pudo conectar a la BD"}), 500

        # Pasamos el engine a la función
        success, message = save_dataframe_to_db(df_to_save, "ventas_historicas", engine)

        if success:
            # Devolvemos un resumen (esto lo lee el frontend)
            summary = {
                "filas_guardadas": len(df_to_save),
                "primera_fecha": str(df_to_save['fecha'].min()),
                "ultima_fecha": str(df_to_save['fecha'].max())
            }
            return jsonify(summary), 201 # 201 = Creado
        else:
            # save_dataframe_to_db ya nos dio un mensaje de error
            return jsonify({"error": message}), 500

    except Exception as e:
        # --- Captura de Errores General ---
        logging.error(f"[ERROR /upload] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno: {e}"}), 500

# --- Endpoint 2: /predict (HU-003) ---
@api_bp.route('/predict', methods=['POST'])
def predict():
    """
    Recibe un ID de producto y una fecha, y devuelve
    la predicción del modelo.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibió payload de JSON"}), 400
            
        id_producto = data.get('id_producto')
        fecha_str = data.get('fecha_str')

        if not id_producto or not fecha_str:
            return jsonify({"error": "Faltan 'id_producto' o 'fecha_str'"}), 400

        # Llamar a nuestra lógica de ML
        prediccion = make_single_prediction(id_producto, fecha_str)

        if prediccion is None:
            # Esto maneja el caso de que el ID de producto sea desconocido
            logging.warning(f"Predicción fallida para {id_producto} (probablemente ID desconocido)")
            return jsonify({"error": f"No se pudo generar la predicción. ¿El ID '{id_producto}' es correcto y fue parte del entrenamiento?"}), 404
        
        # ¡Éxito!
        return jsonify({"prediccion": prediccion}), 200

    except Exception as e:
        # --- Captura de Errores General ---
        # ¡Esta es la corrección clave para tu error!
        logging.error(f"[ERROR /predict] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno en la predicción: {e}"}), 500

# --- Endpoint 3: /history (HU-003) ---
@api_bp.route('/history', methods=['POST'])
def get_history():
    """
    Recibe un ID de producto y devuelve su historial de ventas
    de la base de datos.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibió payload de JSON"}), 400
            
        id_producto = data.get('id_producto')

        if not id_producto:
            return jsonify({"error": "Falta 'id_producto'"}), 400

        engine = get_db_engine()
        if engine is None:
            return jsonify({"error": "Error interno: No se pudo conectar a la BD"}), 500

        # Consulta segura para evitar Inyección SQL (usando params)
        query = "SELECT fecha, cantidad_vendida FROM ventas_historicas WHERE id_producto = %s ORDER BY fecha ASC"
        
        df_hist = pd.read_sql(
            query,
            con=engine,
            params=(id_producto,) # Parámetro sanitizado
        )
        
        # Convertir a JSON
        historial = df_hist.to_dict('records')
        
        # Convertir fechas a string (JSON no maneja objetos datetime)
        for record in historial:
            # Asegurarse de que 'fecha' es un objeto datetime antes de llamar .isoformat()
            if isinstance(record['fecha'], (pd.Timestamp, pd.Period)):
                record['fecha'] = record['fecha'].isoformat()
            
        return jsonify({"historial": historial}), 200

    except Exception as e:
        # --- Captura de Errores General ---
        # ¡Esta es la otra corrección clave!
        logging.error(f"[ERROR /history] {e}", exc_info=True)
        return jsonify({"error": f"Ocurrió un error interno en el historial: {e}"}), 500

