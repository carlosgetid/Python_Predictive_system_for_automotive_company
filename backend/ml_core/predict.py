import joblib
import os
import pandas as pd
import numpy as np
import logging
from tensorflow.keras.models import load_model
from datetime import datetime
import tensorflow as tf # Importar tf

# --- 1. Constantes y Carga de Artefactos (MVP) ---

MODELS_DIR = "models"
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "min_max_scaler.joblib")
MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras") 

# --- INICIO DE LA MODIFICACIÓN (RECARGA EN VIVO) ---

# Caché global para mantener los artefactos en memoria
# Usamos un diccionario para poder verificar si está vacío o no.
artifacts_cache = {}

def load_artifacts_into_memory():
    """
    Carga todos los artefactos de preprocesamiento y el modelo entrenado
    desde el disco y los almacena en la caché global 'artifacts_cache'.
    
    Returns:
        bool: True si la carga fue exitosa, False si falló.
    """
    global artifacts_cache # Indicar que estamos modificando la variable global
    
    artifacts_temp = {} # Diccionario temporal
    try:
        # Limpiar logs de TensorFlow antes de cargar el modelo
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        tf.get_logger().setLevel('ERROR')

        if not os.path.exists(ENCODER_PATH):
            raise FileNotFoundError(f"No se encontró el encoder en {ENCODER_PATH}")
        artifacts_temp['encoder'] = joblib.load(ENCODER_PATH)

        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(f"No se encontró el scaler en {SCALER_PATH}")
        artifacts_temp['scaler'] = joblib.load(SCALER_PATH)

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"No se encontró el modelo MLP en {MODEL_PATH}")
        # Cargar el modelo. Es importante limpiar sesiones anteriores si Keras se queja.
        tf.keras.backend.clear_session()
        artifacts_temp['model'] = load_model(MODEL_PATH)

        logging.info("Artefactos de ML (MVP: encoder, scaler, model MLP) cargados/recargados con éxito.")
        
        # Actualizar la caché global de forma atómica
        artifacts_cache = artifacts_temp
        return True

    except FileNotFoundError as e:
        logging.error(f"Error crítico al cargar artefactos: {e}. Asegúrate de ejecutar el pipeline de entrenamiento.")
        artifacts_cache = {} # Limpiar caché en caso de fallo
        return False
    except Exception as e:
        logging.error(f"Error inesperado al cargar artefactos: {e}", exc_info=True)
        artifacts_cache = {}
        return False

def reload_artifacts():
    """
    Función pública expuesta para forzar la recarga de los artefactos
    (llamada después del re-entrenamiento por routes.py).
    """
    logging.info("Solicitud de recarga de artefactos recibida...")
    return load_artifacts_into_memory()

# --- Carga inicial de artefactos ---
# Se ejecuta UNA SOLA VEZ cuando el backend (app.py) importa este archivo.
if not load_artifacts_into_memory():
    logging.critical("¡FALLO EN LA CARGA INICIAL DE ARTEFACTOS! El endpoint /predict no funcionará.")

# --- FIN DE LA MODIFICACIÓN (RECARGA EN VIVO) ---


# --- 2. Lógica de Predicción (Replicar Preprocesamiento MVP) ---

def make_single_prediction(id_producto, fecha_str):
    """
    Realiza una predicción de demanda (cantidad) para un solo producto y fecha (MVP).
    """
    # --- CAMBIO: Verificar la caché global ---
    if not artifacts_cache:
        logging.error("Artefactos no están cargados en memoria. Abortando predicción.")
        return None

    # Obtener artefactos de la caché global
    encoder = artifacts_cache.get('encoder')
    scaler = artifacts_cache.get('scaler')
    model = artifacts_cache.get('model')

    if not all([encoder, scaler, model]):
         logging.error("Uno o más artefactos (encoder, scaler, model) faltan en la caché. Abortando predicción.")
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
        # Aplicar transformación, asignar -1 a desconocidos (LabelEncoder no maneja desconocidos nativamente)
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
    # (La carga inicial de artefactos ya se habrá ejecutado al importar)

    # Probamos con un ID de producto que SÍ debería existir si los datos son los mismos
    id_prueba_1 = "SKU-2021-00010-3398" # Ajusta si tu encoder tiene otros productos
    fecha_prueba = "2025-11-20" # Una fecha futura razonable

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

