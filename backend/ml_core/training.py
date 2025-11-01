import pandas as pd
import numpy as np
import os
import joblib
import logging # Importar logging
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# --- Importar Modelos ---
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
# Importar EarlyStopping para un mejor entrenamiento
from tensorflow.keras.callbacks import EarlyStopping

# --- Importar nuestro preprocesador (Revertido a MVP) ---
from backend.ml_core.preprocessing import get_and_preprocess_data

# --- Constantes (Revertidas a MVP) ---
MODELS_DIR = "models"
# Nombres originales de los modelos
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.joblib")
MLP_MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras")

# --- Tarea HU-002.T3: Lógica de Evaluación (Modificada) ---
def evaluate_model(y_true, y_pred, model_name):
    """
    Calcula, registra (logs) y DEVUELVE las métricas de regresión.
    """
    y_pred = np.maximum(0, y_pred) # Predicciones no pueden ser negativas

    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = max(0.0, r2_score(y_true, y_pred)) # Evitar R² negativo

    # --- CAMBIO: Usar logging en lugar de print ---
    logging.info(f"--- Métricas de Evaluación para {model_name} ---")
    logging.info(f"MAE (Error Absoluto Medio): {mae:.2f} unidades")
    logging.info(f"RMSE (Error Cuadrático Medio Raíz): {rmse:.2f} unidades")
    logging.info(f"R² (Coeficiente de Determinación): {r2:.2f}")
    logging.info("--------------------------------------------------")

    # --- CAMBIO: Devolver diccionario con nombre de modelo ---
    return {"model": model_name, "mae": mae, "rmse": rmse, "r2": r2}

# --- Tarea HU-002.T1: Entrenamiento XGBoost (Modificado) ---
def train_xgboost(X_train, y_train):
    """
    Entrena un modelo XGBoost Regressor (lógica MVP).
    """
    # --- CAMBIO: Usar logging en lugar de print ---
    logging.info("\nIniciando entrenamiento de XGBoost (lógica MVP)...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror', 
        n_estimators=100,             
        learning_rate=0.1,            
        max_depth=5,                  
        random_state=42               
    )

    try:
        model.fit(X_train, y_train)
        logging.info("Entrenamiento de XGBoost completado.")
        return model
    except Exception as e:
        logging.error(f"Error durante el entrenamiento de XGBoost: {e}", exc_info=True)
        return None


# --- Tarea HU-002.T2: Entrenamiento MLP (Modificado) ---
def train_mlp(X_train, y_train):
    """
    Entrena un modelo MLP con Keras (lógica MVP).
    """
    # --- CAMBIO: Usar logging en lugar de print ---
    logging.info("\nIniciando entrenamiento de MLP (Red Neuronal - lógica MVP)...")

    n_features = X_train.shape[1]
    if n_features == 0:
        logging.error("X_train no tiene features para entrenar MLP.")
        return None

    model = Sequential([
        Input(shape=(n_features,)), 
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(1, activation='linear') 
    ])

    model.compile(
        optimizer=Adam(learning_rate=0.001), 
        loss='mean_squared_error' 
    )

    logging.info("Arquitectura del modelo MLP (MVP):")
    model.summary(print_fn=logging.info) # Usar logging para summary

    epochs = 100 
    batch_size = max(4, min(32, len(X_train) // 10)) 

    # --- CAMBIO: Usar callbacks (el código que me diste no lo tenía) ---
    callbacks = [
        EarlyStopping(
            monitor='val_loss', 
            patience=10,        
            restore_best_weights=True, 
            verbose=1
        )
    ]

    try:
        history = model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2, 
            verbose=1,            
            callbacks=callbacks   # Usar parada temprana
        )
        logging.info("Entrenamiento de MLP completado.")
        return model
    except Exception as e:
         logging.error(f"Error durante el entrenamiento del MLP: {e}", exc_info=True)
         return None

# --- Orquestador Principal de Entrenamiento (Modificado para devolver JSON) ---
def train_and_evaluate():
    """
    Función principal que orquesta el pipeline MVP.
    ACTUALIZADO: Ahora devuelve un diccionario con el estado y las métricas.
    """
    # --- CAMBIO: Usar logging en lugar de print ---
    logging.info("--- INICIANDO PIPELINE DE ENTRENAMIENTO (lógica MVP) ---")

    # 1. Cargar y preprocesar datos
    data_split = get_and_preprocess_data(for_training=True)
    if data_split is None:
        error_msg = "Fallo en la carga/preprocesamiento de datos. Abortando entrenamiento."
        logging.error(error_msg)
        # --- CAMBIO: Devolver estado de error ---
        return {"status": "error", "message": error_msg}

    X_train, X_test, y_train, y_test = data_split

    if X_train.empty or X_test.empty:
        error_msg = "No hay suficientes datos para entrenamiento o prueba después de dividir."
        logging.warning(error_msg)
        # --- CAMBIO: Devolver estado de error ---
        return {"status": "error", "message": error_msg}

    # 2. Entrenar XGBoost (T1)
    model_xgb = train_xgboost(X_train, y_train)
    if model_xgb is None:
        logging.warning("Fallo el entrenamiento de XGBoost. No se guardará este modelo.")

    # 3. Entrenar MLP (T2)
    model_mlp = train_mlp(X_train.values, y_train.values)
    if model_mlp is None:
         logging.warning("Fallo el entrenamiento del MLP. No se guardará este modelo.")
    
    # --- CAMBIO: Verificar si ambos fallaron ---
    if model_xgb is None and model_mlp is None:
        error_msg = "Ambos entrenamientos (XGBoost y MLP) fallaron."
        logging.error(error_msg)
        return {"status": "error", "message": error_msg}


    logging.info("\n--- EVALUACIÓN DE MODELOS (MVP) EN DATOS DE PRUEBA ---")

    # --- CAMBIO: Capturar métricas y estado ---
    all_metrics = [] # Lista para guardar los diccionarios de métricas

    # 4. Evaluar XGBoost (T3)
    if model_xgb:
        y_pred_xgb = model_xgb.predict(X_test)
        metrics_xgb = evaluate_model(y_test, y_pred_xgb, "XGBoost (MVP)")
        all_metrics.append(metrics_xgb) # Añadir métricas a la lista

    # 5. Evaluar MLP (T3)
    if model_mlp:
        try:
            y_pred_mlp = model_mlp.predict(X_test.values).flatten()
            metrics_mlp = evaluate_model(y_test, y_pred_mlp, "MLP (Keras - MVP)")
            all_metrics.append(metrics_mlp) # Añadir métricas a la lista
        except Exception as e:
            logging.error(f"Error durante la evaluación del MLP: {e}", exc_info=True)


    # 6. Guardar (T4)
    logging.info("\nGuardando modelos MVP entrenados (si el entrenamiento fue exitoso)...")

    save_status = [] # Lista para guardar el estado del guardado

    # Guardar XGBoost si existe
    if model_xgb:
        try:
            joblib.dump(model_xgb, XGB_MODEL_PATH)
            logging.info(f"Modelo XGBoost (MVP) guardado en: {XGB_MODEL_PATH}")
            save_status.append(f"XGBoost guardado en {XGB_MODEL_PATH}")
        except Exception as e:
            logging.error(f"Error al guardar modelo XGBoost: {e}", exc_info=True)
            save_status.append(f"Error al guardar XGBoost: {e}")
    else:
        # Eliminar versión antigua si el entrenamiento falló
        if os.path.exists(XGB_MODEL_PATH):
            try:
                os.remove(XGB_MODEL_PATH)
                logging.info(f"Modelo XGBoost anterior eliminado ({XGB_MODEL_PATH}).")
            except OSError as e:
                logging.error(f"Error al eliminar modelo XGBoost anterior: {e}")

    # Guardar MLP si existe
    if model_mlp:
        try:
            model_mlp.save(MLP_MODEL_PATH)
            logging.info(f"Modelo MLP (MVP) guardado en: {MLP_MODEL_PATH}")
            save_status.append(f"MLP guardado en {MLP_MODEL_PATH}")
        except Exception as e:
             logging.error(f"Error al guardar modelo MLP: {e}", exc_info=True)
             save_status.append(f"Error al guardar MLP: {e}")
    else:
        # Eliminar versión antigua si el entrenamiento falló
        if os.path.exists(MLP_MODEL_PATH):
             try:
                # Keras model .keras es un archivo (en versiones recientes), no un directorio
                os.remove(MLP_MODEL_PATH)
                logging.info(f"Modelo MLP anterior eliminado ({MLP_MODEL_PATH}).")
             except OSError as e:
                  logging.error(f"Error al eliminar modelo MLP anterior: {e}")


    logging.info("--- PIPELINE DE ENTRENAMIENTO (MVP) COMPLETADO ---")
    
    # --- CAMBIO: Devolver el reporte final ---
    return {
        "status": "success",
        "message": "Entrenamiento completado.",
        "save_status": save_status,
        "metrics": all_metrics
    }

# --- Bloque de prueba (Modificado para imprimir el JSON) ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO) 
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    tf.get_logger().setLevel('ERROR')

    # --- CAMBIO: Capturar e imprimir el resultado ---
    results = train_and_evaluate()
    print("\n--- RESULTADO DEL PIPELINE (JSON) ---")
    import json
    # Imprimir el JSON de forma legible
    print(json.dumps(results, indent=2))

