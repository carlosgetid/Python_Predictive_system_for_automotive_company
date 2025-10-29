import joblib
import os
import pandas as pd
import numpy as np
import logging
from tensorflow.keras.models import load_model
from datetime import datetime

# --- 1. Constantes y Carga de Artefactos (MVP) ---

MODELS_DIR = "models"
# Nombres originales de los artefactos del MVP
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "min_max_scaler.joblib")
# Usaremos el modelo MLP por defecto para las predicciones
MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras")

def load_artifacts():
    """
    Carga los artefactos del MVP (encoder, scaler, model) desde el disco.
    """
    artifacts = {}
    try:
        if not os.path.exists(ENCODER_PATH):
            raise FileNotFoundError(f"No se encontró el encoder en {ENCODER_PATH}")
        artifacts['encoder'] = joblib.load(ENCODER_PATH)

        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(f"No se encontró el scaler en {SCALER_PATH}")
        artifacts['scaler'] = joblib.load(SCALER_PATH)

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"No se encontró el modelo MLP en {MODEL_PATH}")
        artifacts['model'] = load_model(MODEL_PATH)

        logging.info("Artefactos de ML (MVP: encoder, scaler, model MLP) cargados con éxito.")
        return artifacts

    except FileNotFoundError as e:
        logging.error(f"Error crítico: {e}. Asegúrate de ejecutar el pipeline de entrenamiento (training.py) primero.")
        return None # Indica fallo en la carga
    except Exception as e:
        logging.error(f"Error inesperado al cargar artefactos: {e}", exc_info=True)
        return None

# --- Cargamos los artefactos UNA SOLA VEZ ---
artifacts = load_artifacts()
# Ahora accedemos a ellos como artifacts['encoder'], artifacts['scaler'], artifacts['model']

# --- 2. Lógica de Predicción (Replicar Preprocesamiento MVP) ---

def make_single_prediction(id_producto, fecha_str):
    """
    Realiza una predicción de demanda (cantidad) para un solo producto y fecha (MVP).

    Args:
        id_producto (str): El SKU del producto (ej. "FIL-A-001").
        fecha_str (str): La fecha para la predicción (ej. "2025-11-20").

    Returns:
        int: La cantidad de demanda predicha (redondeada hacia arriba).
        None: Si ocurre un error o el producto es desconocido.
    """
    # Verificar si los artefactos se cargaron correctamente
    if artifacts is None:
        logging.error("Artefactos no cargados. Abortando predicción.")
        return None

    encoder = artifacts.get('encoder')
    scaler = artifacts.get('scaler')
    model = artifacts.get('model')

    if not all([encoder, scaler, model]):
         logging.error("Uno o más artefactos (encoder, scaler, model) faltan. Abortando predicción.")
         return None


    try:
        # --- Paso A: Replicar Ingeniería de Características (MVP) ---
        try:
            fecha = pd.to_datetime(fecha_str)
        except ValueError:
            logging.error(f"Formato de fecha inválido: {fecha_str}. Use YYYY-MM-DD.")
            return None # Error si la fecha no es válida

        data = {
            'id_producto': [str(id_producto)], # Asegurar que sea string
            'mes': [fecha.month],
            'dia_del_mes': [fecha.day],
            'dia_de_la_semana': [fecha.dayofweek],
            'anio': [fecha.year]
        }

        # Orden exacto esperado por el scaler del MVP
        column_order = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']
        df_pred = pd.DataFrame(data, columns=column_order)

        # --- Paso B: Replicar Codificación (MVP con manejo de desconocidos) ---
        known_labels = set(encoder.classes_)
        id_prod_encoded = encoder.transform([str(id_producto)])[0] if str(id_producto) in known_labels else -1

        if id_prod_encoded == -1:
            logging.warning(f"ID de producto desconocido: {id_producto}. No se puede realizar la predicción.")
            return None # Devolvemos None si el producto no se vio en entrenamiento

        df_pred['id_producto'] = id_prod_encoded # Reemplazar string con el código numérico

        # --- Paso C: Replicar Escalado (MVP) ---
        # Asegurarse que todas las columnas son numéricas antes de escalar
        for col in column_order:
             df_pred[col] = pd.to_numeric(df_pred[col], errors='coerce')

        if df_pred.isnull().values.any():
             logging.error("Valores no numéricos encontrados antes de escalar.")
             return None # Error si hay nulos después de convertir a numérico

        # Aplicar el escalado aprendido
        df_scaled = scaler.transform(df_pred) # Scaler espera todas las 5 columnas numéricas

        # --- Paso D: Realizar la Predicción con MLP ---
        prediction_raw = model.predict(df_scaled)
        prediction_value = prediction_raw[0][0]

        # La predicción de cantidad no puede ser negativa
        prediction_value = max(0, prediction_value)

        # Redondear hacia ARRIBA (techo) para ser conservador con el inventario
        prediction_final = int(np.ceil(prediction_value))

        logging.info(f"Predicción (MVP) generada para {id_producto} en {fecha_str}: {prediction_final} unidades")
        return prediction_final

    except Exception as e:
        logging.error(f"Error inesperado durante la predicción: {e}", exc_info=True)
        return None

# --- Bloque de prueba (Opcional) ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    tf.get_logger().setLevel('ERROR')

    # Probamos con un ID de producto que SÍ debería existir si los datos son los mismos
    id_prueba_1 = "FIL-A-001" # Ajusta si tu encoder tiene otros productos
    fecha_prueba = "2024-11-20" # Una fecha futura razonable

    prediccion = make_single_prediction(id_prueba_1, fecha_prueba)
    if prediccion is not None:
        print(f"\n--- PRUEBA DE PREDICCIÓN (MVP) ---")
        print(f"Predicción para {id_prueba_1} en {fecha_prueba}: {prediccion} unidades")
        print("----------------------------------\n")
    else:
         print(f"Fallo la predicción para {id_prueba_1}. ¿El producto existe en los datos de entrenamiento y los artefactos están cargados?")


    # Probamos con un ID de producto que NO existe
    id_prueba_2 = "PRODUCTO-NUEVO-XYZ"
    print(f"Probando con producto desconocido: {id_prueba_2}...")
    prediccion_nueva = make_single_prediction(id_prueba_2, fecha_prueba)
    if prediccion_nueva is None:
        print("Prueba exitosa: El producto no se encontró, como se esperaba.")
    else:
        print(f"Error en la prueba: Se obtuvo una predicción ({prediccion_nueva}) para un producto desconocido.")
