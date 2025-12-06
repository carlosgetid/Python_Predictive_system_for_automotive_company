import joblib
import os
import pandas as pd
import numpy as np
import logging
from tensorflow.keras.models import load_model
import tensorflow as tf
import xgboost as xgb # --- NUEVO: Importar XGBoost

# --- 1. Constantes y Carga de Artefactos ---

MODELS_DIR = "models"
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "min_max_scaler.joblib")
MLP_MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras") 
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.joblib") # --- NUEVO: Ruta XGBoost

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

        # --- INICIO AGREGADO XGBOOST ---
        if not os.path.exists(XGB_MODEL_PATH):
             # Advertencia no crítica si falta uno, pero idealmente deberían estar ambos
             logging.warning(f"No se encontró modelo XGBoost en {XGB_MODEL_PATH}")
        else:
             artifacts_temp['xgboost'] = joblib.load(XGB_MODEL_PATH)
        # --- FIN AGREGADO XGBOOST ---

        if not os.path.exists(MLP_MODEL_PATH):
            raise FileNotFoundError(f"No se encontró el modelo MLP en {MLP_MODEL_PATH}")
        
        tf.keras.backend.clear_session()
        artifacts_temp['mlp'] = load_model(MLP_MODEL_PATH) # Cambié la clave a 'mlp' para ser específico

        logging.info("Artefactos de ML (Encoder, Scaler, MLP, XGBoost) cargados/recargados con éxito.")
        
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
    # --- CAMBIO: Obtener los modelos específicos ---
    model_mlp = artifacts_cache.get('mlp')
    model_xgb = artifacts_cache.get('xgboost')

    # Validar que existan los transformadores y al menos un modelo
    if not encoder or not scaler:
         logging.error("Faltan artefactos esenciales (encoder o scaler) en la caché. Abortando predicción.")
         return None
         
    if not model_mlp and not model_xgb:
         logging.error("No hay ningún modelo (MLP o XGBoost) cargado en la caché. Abortando predicción.")
         return None


    try:
        # --- Paso A: Ingeniería de Características ---
        try:
            fecha = pd.to_datetime(fecha_str)
        except ValueError:
            logging.error(f"Formato de fecha inválido: {fecha_str}. Use YYYY-MM-DD.")
            return None

        # --- Paso B: Codificación (Primero obtenemos el valor) ---
        known_labels = set(encoder.classes_)
        # Si el producto no existe en el encoder, devolvemos -1
        id_prod_encoded = encoder.transform([str(id_producto)])[0] if str(id_producto) in known_labels else -1

        if id_prod_encoded == -1:
            logging.warning(f"ID de producto desconocido: {id_producto}. No se puede predecir.")
            return None 

        # --- Paso C: Construcción del DataFrame (CORRECCIÓN DE NOMBRES HU-006) ---
        # Los nombres deben coincidir EXACTAMENTE con los usados en training.py:
        # ['id_producto_encoded', 'mes', 'anio', 'dia_semana', 'dia']
        
        data = {
            'id_producto_encoded': [id_prod_encoded],
            'mes': [fecha.month],
            'anio': [fecha.year],
            'dia_semana': [fecha.dayofweek],  # Antes: dia_de_la_semana
            'dia': [fecha.day]                # Antes: dia_del_mes
        }

        # Orden explícito igual al del entrenamiento
        column_order = ['id_producto_encoded', 'mes', 'anio', 'dia_semana', 'dia']
        
        df_pred = pd.DataFrame(data, columns=column_order)

        # --- Paso D: Escalado ---
        # Ahora los nombres coinciden, el scaler funcionará
        df_scaled = scaler.transform(df_pred)

        # --- Paso D: Realizar la Predicción Híbrida (XGBoost + MLP) ---
        
        # 1. Obtener modelos de la caché
        model_mlp = artifacts_cache.get('mlp')
        model_xgb = artifacts_cache.get('xgboost')
        
        # --- Paso D: Realizar la Predicción Híbrida (XGBoost + MLP) ---
        preds = []
        
        # 1. Predicción MLP
        if model_mlp:
            try:
                # Keras/MLP devuelve una matriz [[valor]], extraemos el float
                pred_mlp = model_mlp.predict(df_scaled, verbose=0)[0][0]
                preds.append(pred_mlp)
            except Exception as e:
                logging.error(f"Error prediciendo con MLP: {e}")

        # 2. Predicción XGBoost
        if model_xgb:
            try:
                # XGBoost devuelve un array [valor], extraemos el float
                pred_xgb = model_xgb.predict(df_scaled)[0]
                preds.append(pred_xgb)
            except Exception as e:
                logging.error(f"Error prediciendo con XGBoost: {e}")
            
        if not preds:
            logging.error("Falló la predicción: no se pudo obtener resultado de ningún modelo.")
            return None

        # 3. Promedio (Ensamble)
        prediction_value = sum(preds) / len(preds)

        # La predicción de cantidad no puede ser negativa
        prediction_value = max(0, prediction_value)

        # Redondear hacia ARRIBA (techo) para ser conservador con el inventario
        prediction_final = int(np.ceil(prediction_value))

        logging.info(f"Predicción Híbrida para {id_producto} en {fecha_str}: {prediction_final} unidades")
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

