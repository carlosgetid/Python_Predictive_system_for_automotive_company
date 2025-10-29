import joblib
import os
import pandas as pd
import numpy as np
import logging
from tensorflow.keras.models import load_model
from datetime import datetime

# --- 1. Constantes y Carga de Artefactos ---

# Definimos las rutas a los artefactos que guardamos en la HU-002
MODELS_DIR = "models"
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "min_max_scaler.joblib")
MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras") # Usaremos el modelo MLP

def load_artifacts():
    """
    Carga todos los artefactos de preprocesamiento y el modelo entrenado
    desde el disco.
    """
    try:
        # Cargar el codificador (para 'id_producto')
        encoder = joblib.load(ENCODER_PATH)
        
        # Cargar el escalador (para normalizar 0-1)
        scaler = joblib.load(SCALER_PATH)
        
        # Cargar el modelo de Red Neuronal entrenado
        model = load_model(MODEL_PATH)
        
        logging.info("Artefactos de ML (encoder, scaler, model) cargados con éxito.")
        return encoder, scaler, model
    
    except FileNotFoundError:
        logging.error("Error crítico: No se encontraron los archivos del modelo. "
                      "Asegúrate de ejecutar el pipeline de entrenamiento (training.py) primero.")
        return None, None, None
    except Exception as e:
        logging.error(f"Error al cargar artefactos: {e}")
        return None, None, None

# --- Cargamos los artefactos UNA SOLA VEZ cuando el script se importa ---
# Esto es mucho más eficiente que cargarlos en cada predicción.
encoder, scaler, model = load_artifacts()

# --- 2. Lógica de Predicción (Replicar Preprocesamiento) ---

def make_single_prediction(id_producto, fecha_str):
    """
    Realiza una predicción de demanda para un solo producto y fecha.
    
    Args:
        id_producto (str): El SKU del producto (ej. "FIL-A-001").
        fecha_str (str): La fecha para la predicción (ej. "2025-11-20").
        
    Returns:
        int: La cantidad de demanda predicha (redondeada hacia arriba).
        None: Si ocurre un error.
    """
    if model is None or encoder is None or scaler is None:
        logging.error("Modelos no cargados. Abortando predicción.")
        return None

    try:
        # --- Paso A: Replicar la Ingeniería de Características ---
        # (Exactamente como en preprocessing.py)
        fecha = pd.to_datetime(fecha_str)
        data = {
            'id_producto': [id_producto],
            'mes': [fecha.month],
            'dia_del_mes': [fecha.day],
            'dia_de_la_semana': [fecha.dayofweek],
            'anio': [fecha.year]
        }
        
        # Creamos un DataFrame con los nombres de columnas exactos que el
        # escalador espera, en el orden correcto.
        column_order = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']
        df_pred = pd.DataFrame(data, columns=column_order)

        # --- Paso B: Replicar el Preprocesamiento (Codificación) ---
        # Usamos .transform() para aplicar la codificación ya aprendida.
        # Añadimos manejo de error por si el 'id_producto' es nuevo.
        try:
            df_pred['id_producto'] = encoder.transform(df_pred['id_producto'])
        except ValueError as e:
            # Este error ocurre si el 'id_producto' es desconocido (ej. 'NUEVO-PROD-001')
            logging.warning(f"ID de producto desconocido: {id_producto}. "
                            f"No se puede realizar la predicción. Error: {e}")
            # En un caso real, podríamos devolver 0 o un valor por defecto.
            # Por ahora, para el MVP, devolvemos None.
            return None

        # --- Paso C: Replicar el Preprocesamiento (Escalado) ---
        # Usamos .transform() para escalar los datos usando el min/max ya aprendido.
        # El escalador espera un DataFrame con todas las columnas numéricas.
        df_scaled = scaler.transform(df_pred)
        
        # --- Paso D: Realizar la Predicción ---
        # El modelo Keras espera un array de NumPy
        prediction_raw = model.predict(df_scaled)
        
        # El resultado de Keras es un array 2D (ej. [[23.45]]), lo extraemos
        prediction_value = prediction_raw[0][0]
        
        # No podemos predecir una cantidad negativa
        if prediction_value < 0:
            prediction_value = 0
            
        # Redondeamos hacia ARRIBA (techo). Para inventario, es más seguro
        # predecir 24 unidades que 23, si el modelo dice 23.4.
        prediction_final = int(np.ceil(prediction_value))
        
        logging.info(f"Predicción generada para {id_producto} en {fecha_str}: {prediction_final}")
        return prediction_final

    except Exception as e:
        logging.error(f"Error durante la predicción: {e}")
        return None

# --- Bloque de prueba (Opcional) ---
if __name__ == "__main__":
    # Esto te permite probar el archivo directamente
    # python -m backend.ml_core.predict
    logging.basicConfig(level=logging.INFO)
    
    # Probamos con un ID de producto que SÍ existe en los datos de prueba
    id_prueba_1 = "FIL-A-001" 
    fecha_prueba = "2025-11-20"
    
    prediccion = make_single_prediction(id_prueba_1, fecha_prueba)
    if prediccion is not None:
        print(f"\n--- PRUEBA DE PREDICCIÓN ---")
        print(f"Predicción para {id_prueba_1} en {fecha_prueba}: {prediccion}")
        print("--------------------------\n")
        
    # Probamos con un ID de producto que NO existe
    id_prueba_2 = "PRODUCTO-NUEVO-XYZ"
    print(f"Probando con producto desconocido: {id_prueba_2}")
    prediccion_nueva = make_single_prediction(id_prueba_2, fecha_prueba)
    if prediccion_nueva is None:
        print("Prueba exitosa: El producto no se encontró, como se esperaba.")

