import pandas as pd
import numpy as np
import os
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# --- Importar Modelos ---
# T1: XGBoost
import xgboost as xgb

# T2: MLP (Red Neuronal) con TensorFlow/Keras
# (Asegúrate de que 'tensorflow' esté en tu requirements.txt y venv)
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam

# --- Importar nuestro preprocesador ---
from backend.ml_core.preprocessing import get_and_preprocess_data

# --- Constantes ---
MODELS_DIR = "models" 
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.joblib")
MLP_MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras")

# --- Tarea HU-002.T3: Lógica de Evaluación ---

def evaluate_model(y_true, y_pred, model_name):
    """
    Calcula y muestra las métricas de regresión (MAE, RMSE, R²) para un modelo.
    """
    # Calcular métricas
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    # Imprimir resultados
    print(f"--- Métricas de Evaluación para {model_name} ---")
    print(f"MAE (Error Absoluto Medio): {mae:.2f}")
    print(f"RMSE (Error Cuadrático Medio Raíz): {rmse:.2f}")
    print(f"R² (Coeficiente de Determinación): {r2:.2f}")
    print("--------------------------------------------------")
    
    # Devolver un diccionario de métricas para comparación
    return {"mae": mae, "rmse": rmse, "r2": r2}

# --- Tarea HU-002.T1: Entrenamiento XGBoost ---

def train_xgboost(X_train, y_train):
    """
    Entrena un modelo XGBoost Regressor.
    """
    print("\nIniciando entrenamiento de XGBoost...")
    # Hiperparámetros básicos (una futura HU podría optimizar esto)
    model = xgb.XGBRegressor(
        objective='reg:squarederror', # Objetivo: regresión
        n_estimators=100,             # Número de árboles
        learning_rate=0.1,            # Tasa de aprendizaje
        max_depth=5,                  # Profundidad máxima
        random_state=42
    )
    
    model.fit(X_train, y_train)
    print("Entrenamiento de XGBoost completado.")
    return model

# --- Tarea HU-002.T2: Entrenamiento MLP (Red Neuronal) ---

def train_mlp(X_train, y_train):
    """
    Entrena un modelo de Red Neuronal (Perceptrón Multicapa) con Keras.
    """
    print("\nIniciando entrenamiento de MLP (Red Neuronal)...")
    
    # Definir la arquitectura de la red
    n_features = X_train.shape[1] # Número de características (deberían ser 5)
    
    model = Sequential([
        # Capa de entrada
        Input(shape=(n_features,)),
        
        # Capas ocultas (dos capas densas)
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        
        # Capa de salida (una neurona, activación lineal para regresión)
        Dense(1, activation='linear')
    ])
    
    # Compilar el modelo
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mean_squared_error' # Usamos MSE como función de pérdida
    )
    
    # Entrenar el modelo
    # Con 14 filas, 50 épocas es más que suficiente.
    model.fit(
        X_train, 
        y_train, 
        epochs=50, 
        batch_size=4, 
        validation_split=0.2, # Usa 20% de los datos de entreno para validar
        verbose=1              # Muestra el progreso
    )
    
    print("Entrenamiento de MLP completado.")
    return model

# --- Orquestador Principal de Entrenamiento ---

def train_and_evaluate():
    """
    Función principal que orquesta todo el pipeline:
    1. Carga y preprocesa los datos (desde HU-005).
    2. Entrena el modelo XGBoost (T1).
    3. Entrena el modelo MLP (T2).
    4. Evalúa ambos modelos (T3).
    5. Guarda los modelos (T4).
    """
    print("--- INICIANDO PIPELINE DE ENTRENAMIENTO ---")
    
    # 1. Cargar y preprocesar datos
    data_split = get_and_preprocess_data(for_training=True)
    if data_split is None:
        print("Fallo en la carga de datos. Abortando entrenamiento.")
        return
        
    X_train, X_test, y_train, y_test = data_split
    
    # 2. Entrenar XGBoost (T1)
    model_xgb = train_xgboost(X_train, y_train)
    
    # 3. Entrenar MLP (T2)
    # (Usamos .values para asegurar que Keras reciba arrays de NumPy puros)
    model_mlp = train_mlp(X_train.values, y_train.values)
    
    print("\n--- EVALUACIÓN DE MODELOS EN DATOS DE PRUEBA (Test set) ---")
    
    # 4. Evaluar XGBoost (T3)
    y_pred_xgb = model_xgb.predict(X_test)
    metrics_xgb = evaluate_model(y_test, y_pred_xgb, "XGBoost")
    
    # 5. Evaluar MLP (T3)
    # Keras .predict() devuelve un array 2D, lo aplanamos a 1D con .flatten()
    y_pred_mlp = model_mlp.predict(X_test.values).flatten()
    metrics_mlp = evaluate_model(y_test, y_pred_mlp, "MLP (Keras)")
    
    # 6. Comparar y guardar (T4)
    # (Por ahora, guardaremos ambos. Una futura HU podría elegir solo el mejor)
    
    print("\nGuardando modelos entrenados...")
    
    # T4: Guardar XGBoost (usando joblib)
    joblib.dump(model_xgb, XGB_MODEL_PATH)
    print(f"Modelo XGBoost guardado en: {XGB_MODEL_PATH}")
    
    # T4: Guardar MLP (usando el formato nativo de Keras)
    model_mlp.save(MLP_MODEL_PATH)
    print(f"Modelo MLP (Keras) guardado en: {MLP_MODEL_PATH}")
    
    print("--- PIPELINE DE ENTRENAMIENTO COMPLETADO ---")


# --- Bloque de prueba ---
if __name__ == "__main__":
    # Esto nos permite ejecutar el archivo directamente para probarlo
    # python -m backend.ml_core.training
    
    # Configuración de logs de TensorFlow (para limpiar el output)
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' # Oculta warnings
    tf.get_logger().setLevel('ERROR')
    
    train_and_evaluate()
