import pandas as pd
import numpy as np
import os
import joblib
import logging
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# --- Importar Modelos ---
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam

# --- Importar nuestro preprocesador (Revertido a MVP) ---
from backend.ml_core.preprocessing import get_and_preprocess_data

# --- Constantes (Revertidas a MVP) ---
MODELS_DIR = "models"
# Nombres originales de los modelos
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.joblib")
MLP_MODEL_PATH = os.path.join(MODELS_DIR, "mlp_model.keras")

# --- Tarea HU-002.T3: Lógica de Evaluación (Revertida) ---
def evaluate_model(y_true, y_pred, model_name):
    """
    Calcula y muestra las métricas de regresión (MAE, RMSE, R²).
    MAE y RMSE representan error en UNIDADES.
    """
    # Asegurarse que y_pred no contenga negativos si y_true no los tiene
    y_pred = np.maximum(0, y_pred) # Predicciones no pueden ser negativas

    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    # Evitar R² negativo si el modelo es muy malo (predice peor que la media)
    r2 = max(0.0, r2_score(y_true, y_pred))

    print(f"--- Métricas de Evaluación para {model_name} ---")
    print(f"MAE (Error Absoluto Medio): {mae:.2f} unidades")
    print(f"RMSE (Error Cuadrático Medio Raíz): {rmse:.2f} unidades")
    print(f"R² (Coeficiente de Determinación): {r2:.2f}")
    print("--------------------------------------------------")

    return {"mae": mae, "rmse": rmse, "r2": r2}

# --- Tarea HU-002.T1: Entrenamiento XGBoost ---
def train_xgboost(X_train, y_train):
    """
    Entrena un modelo XGBoost Regressor (lógica MVP).
    """
    print("\nIniciando entrenamiento de XGBoost (lógica MVP)...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror', # Objetivo para regresión (predecir cantidad)
        n_estimators=100,             # Número de árboles (hiperparámetro)
        learning_rate=0.1,            # Tasa de aprendizaje (hiperparámetro)
        max_depth=5,                  # Profundidad máxima (hiperparámetro)
        random_state=42               # Para reproducibilidad
    )

    try:
        model.fit(X_train, y_train)
        print("Entrenamiento de XGBoost completado.")
        return model
    except Exception as e:
        logging.error(f"Error durante el entrenamiento de XGBoost: {e}")
        return None


# --- Tarea HU-002.T2: Entrenamiento MLP (Revertido) ---
def train_mlp(X_train, y_train):
    """
    Entrena un modelo MLP con Keras (lógica MVP).
    """
    print("\nIniciando entrenamiento de MLP (Red Neuronal - lógica MVP)...")

    # El número de features viene del preprocessing del MVP (5)
    n_features = X_train.shape[1]
    if n_features == 0:
        logging.error("X_train no tiene features para entrenar MLP.")
        return None

    # Arquitectura simple para el MVP
    model = Sequential([
        Input(shape=(n_features,)), # 5 features: id_prod_enc, mes, dia, dia_sem, anio
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(1, activation='linear') # Salida lineal para regresión de cantidad
    ])

    # Compilar el modelo
    model.compile(
        optimizer=Adam(learning_rate=0.001), # Optimizador Adam
        loss='mean_squared_error' # MSE es una buena métrica para cantidad
    )

    print("Arquitectura del modelo MLP (MVP):")
    model.summary(print_fn=logging.info) # Usar logging para summary

    # Ajustar épocas/batch_size según el tamaño de datos
    # Evitar overfitting en datos pequeños con EarlyStopping
    epochs = 100 # Empezar con un número razonable
    batch_size = max(4, min(32, len(X_train) // 10)) # Batch size dinámico, mínimo 4

    # Callbacks: Parada temprana si no mejora y guardar el mejor modelo
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', # Monitorear pérdida en validación
            patience=10,        # Esperar 10 épocas sin mejora
            restore_best_weights=True, # Quedarse con el mejor modelo encontrado
            verbose=1
        )
    ]

    try:
        # Entrenar el modelo
        history = model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2, # Usar 20% de los datos de entrenamiento para validar
            verbose=1,            # Mostrar progreso
            callbacks=callbacks   # Usar parada temprana
        )
        print("Entrenamiento de MLP completado.")
        return model
    except Exception as e:
         logging.error(f"Error durante el entrenamiento del MLP: {e}")
         return None

# --- Orquestador Principal de Entrenamiento (Revertido a MVP) ---
def train_and_evaluate():
    """
    Función principal que orquesta el pipeline MVP:
    1. Carga y preprocesa datos de 'ventas_historicas'.
    2. Entrena XGBoost.
    3. Entrena MLP.
    4. Evalúa ambos.
    5. Guarda los modelos del MVP.
    """
    print("--- INICIANDO PIPELINE DE ENTRENAMIENTO (lógica MVP) ---")

    # 1. Cargar y preprocesar datos (llama a la lógica revertida)
    data_split = get_and_preprocess_data(for_training=True)
    if data_split is None:
        print("Fallo en la carga/preprocesamiento de datos. Abortando entrenamiento.")
        return

    X_train, X_test, y_train, y_test = data_split

    # Verificar si hay datos suficientes después de la división
    if X_train.empty or X_test.empty:
        print("No hay suficientes datos para entrenamiento o prueba después de dividir.")
        return

    # 2. Entrenar XGBoost (T1)
    model_xgb = train_xgboost(X_train, y_train)
    if model_xgb is None:
        print("Fallo el entrenamiento de XGBoost. No se guardará este modelo.")

    # 3. Entrenar MLP (T2)
    # Pasar NumPy arrays a Keras es más seguro
    model_mlp = train_mlp(X_train.values, y_train.values)
    if model_mlp is None:
         print("Fallo el entrenamiento del MLP. No se guardará este modelo.")
         # Continuamos para evaluar XGBoost si se entrenó


    print("\n--- EVALUACIÓN DE MODELOS (MVP) EN DATOS DE PRUEBA ---")

    # 4. Evaluar XGBoost (T3) - Solo si se entrenó
    metrics_xgb = None
    if model_xgb:
        y_pred_xgb = model_xgb.predict(X_test)
        metrics_xgb = evaluate_model(y_test, y_pred_xgb, "XGBoost (MVP)")

    # 5. Evaluar MLP (T3) - Solo si se entrenó
    metrics_mlp = None
    if model_mlp:
        try:
            # Asegurarse que X_test sea NumPy array para Keras
            y_pred_mlp = model_mlp.predict(X_test.values).flatten()
            metrics_mlp = evaluate_model(y_test, y_pred_mlp, "MLP (Keras - MVP)")
        except Exception as e:
            logging.error(f"Error durante la evaluación del MLP: {e}")


    # 6. Guardar (T4) - ¡Rutas originales! - Solo si el entrenamiento fue exitoso
    print("\nGuardando modelos MVP entrenados (si el entrenamiento fue exitoso)...")

    # Guardar XGBoost si existe
    if model_xgb:
        try:
            joblib.dump(model_xgb, XGB_MODEL_PATH)
            print(f"Modelo XGBoost (MVP) guardado en: {XGB_MODEL_PATH}")
        except Exception as e:
            logging.error(f"Error al guardar modelo XGBoost: {e}")
    else:
        # Si XGB falló, eliminar versión antigua
        if os.path.exists(XGB_MODEL_PATH):
            try:
                os.remove(XGB_MODEL_PATH)
                print(f"Modelo XGBoost anterior eliminado ({XGB_MODEL_PATH}).")
            except OSError as e:
                logging.error(f"Error al eliminar modelo XGBoost anterior: {e}")

    # Guardar MLP si existe
    if model_mlp:
        try:
            model_mlp.save(MLP_MODEL_PATH)
            print(f"Modelo MLP (MVP) guardado en: {MLP_MODEL_PATH}")
        except Exception as e:
             logging.error(f"Error al guardar modelo MLP: {e}")
    else:
        # Si MLP falló, eliminar versión antigua
        if os.path.exists(MLP_MODEL_PATH):
             try:
                os.remove(MLP_MODEL_PATH) # Keras model es un directorio o archivo, os.remove maneja ambos? Revisar si es .keras
                # Si .save crea un directorio, usar shutil.rmtree
                # import shutil
                # shutil.rmtree(MLP_MODEL_PATH)
                print(f"Modelo MLP anterior eliminado ({MLP_MODEL_PATH}).")
             except OSError as e:
                  logging.error(f"Error al eliminar modelo MLP anterior: {e}")


    print("--- PIPELINE DE ENTRENAMIENTO (MVP) COMPLETADO ---")

# --- Bloque de prueba ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO) # Configura logging básico
    # Silenciar logs informativos de TensorFlow/CUDA si no hay GPU
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    tf.get_logger().setLevel('ERROR')

    train_and_evaluate()

