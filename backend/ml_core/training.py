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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from backend.database.db_utils import get_db_engine, save_model_metric # --- NUEVO: save_model_metric
import json # Útil para logs estructurados

# --- Constantes (Revertidas a MVP) ---
MODELS_DIR = "models"
# Nombres originales de los modelos
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.joblib")
MLP_MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras")
SCALER_PATH = os.path.join(MODELS_DIR, "min_max_scaler.joblib")
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder_producto.joblib")

def load_data_from_db():
    """Carga datos frescos desde la BD para re-entrenamiento (HU-006)."""
    engine = get_db_engine()
    if not engine:
        logging.error("No se pudo conectar a la BD.")
        return pd.DataFrame()

    # Consulta optimizada: solo columnas necesarias
    # <-- CAMBIO: Nombre de tabla actualizado a 'ventas_detalle'
    query = "SELECT id_producto, fecha, cantidad_vendida FROM ventas_detalle ORDER BY fecha ASC"
    try:
        df = pd.read_sql(query, engine)
        logging.info(f"Datos cargados de BD: {len(df)} registros.")
        return df
    except Exception as e:
        logging.error(f"Error SQL al cargar datos: {e}")
        return pd.DataFrame()

def preprocess_for_training(df):
    """
    Preprocesa datos y devuelve splits + artefactos (scaler, encoder) para guardar.
    Reemplaza la lógica estática anterior.
    """
    df['fecha'] = pd.to_datetime(df['fecha'])

    # Feature Engineering (Igual que en MVP)
    df['mes'] = df['fecha'].dt.month
    df['anio'] = df['fecha'].dt.year
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['dia'] = df['fecha'].dt.day

    # 1. Encoding (Creamos y ajustamos el encoder aquí)
    le = LabelEncoder()
    df['id_producto_encoded'] = le.fit_transform(df['id_producto'].astype(str))

    features = ['id_producto_encoded', 'mes', 'anio', 'dia_semana', 'dia']
    target = 'cantidad_vendida'

    X = df[features]
    y = df[target]

    # 2. Scaling (Creamos y ajustamos el scaler aquí)
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    return X_train, X_test, y_train, y_test, le, scaler

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

    # 1. Cargar Datos (Desde BD)
    df = load_data_from_db()
    if df.empty:
        return {"status": "error", "message": "La base de datos está vacía o no se pudo leer."}

    # 2. Preprocesar y OBTENER transformadores (Para guardarlos)
    try:
        # Desempaquetamos los 6 valores que devuelve la nueva función
        X_train, X_test, y_train, y_test, label_encoder, scaler = preprocess_for_training(df)
    except Exception as e:
        return {"status": "error", "message": f"Error en preprocesamiento: {e}"}

    if len(X_train) == 0 or len(X_test) == 0:
        error_msg = "No hay suficientes datos para entrenamiento o prueba después de dividir."
        logging.warning(error_msg)
        # --- CAMBIO: Devolver estado de error ---
        return {"status": "error", "message": error_msg}

    # 2. Entrenar XGBoost (T1)
    model_xgb = train_xgboost(X_train, y_train)
    if model_xgb is None:
        logging.warning("Fallo el entrenamiento de XGBoost. No se guardará este modelo.")

    # X_train ya es numpy array, y_train es Series (tiene .values)
    model_mlp = train_mlp(X_train, y_train.values)
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
            y_pred_mlp = model_mlp.predict(X_test).flatten()
            metrics_mlp = evaluate_model(y_test, y_pred_mlp, "MLP (Keras - MVP)")
            all_metrics.append(metrics_mlp) # Añadir métricas a la lista
        except Exception as e:
            logging.error(f"Error durante la evaluación del MLP: {e}", exc_info=True)

    # --- CÁLCULO DE MÉTRICA HÍBRIDA (HU-011) ---
    final_metrics_to_save = None
    
    if model_xgb and model_mlp:
        # Calcular predicción combinada para evaluar el modelo final real
        try:
            pred_xgb = model_xgb.predict(X_test)
            pred_mlp = model_mlp.predict(X_test).flatten()
            
            # Promedio (Lógica de producción)
            hybrid_pred = (pred_xgb + pred_mlp) / 2
            
            # Evaluar Híbrido
            final_metrics_to_save = evaluate_model(y_test, hybrid_pred, "Modelo Híbrido (XGB + MLP)")
            all_metrics.append(final_metrics_to_save)
            
        except Exception as e:
            logging.error(f"Error evaluando modelo híbrido: {e}")

    elif model_xgb:
        # Si solo hay XGB, ese es el final
        final_metrics_to_save = metrics_xgb
    elif model_mlp:
        # Si solo hay MLP, ese es el final
        final_metrics_to_save = metrics_mlp

    # --- GUARDAR EN BD (HU-011) ---
    if final_metrics_to_save:
        try:
            engine = get_db_engine()
            if engine:
                save_model_metric(final_metrics_to_save, engine)
                logging.info("Métricas del modelo final guardadas en BD (HU-011).")
        except Exception as e:
            logging.error(f"No se pudo guardar historial de métricas: {e}")
    # ------------------------------

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
    
    # --- AGREGADO CRÍTICO HU-006: Guardar Transformadores ---
    # Guardamos los "traductores" (Scaler y Encoder) para que el sistema pueda predecir datos futuros
    try:
        joblib.dump(scaler, SCALER_PATH)
        joblib.dump(label_encoder, ENCODER_PATH)
        save_status.append("Scaler y Encoder actualizados.")
        logging.info("Transformadores (Scaler/Encoder) guardados correctamente.")
    except Exception as e:
        logging.error(f"Error guardando transformadores: {e}")
    # ------------------------------------------------------


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