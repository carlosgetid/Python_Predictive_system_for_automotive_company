import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import os

from backend.database.db_utils import get_db_engine, fetch_all_data

# --- Constantes ---
# Definimos las rutas donde guardaremos los "artefactos"
ARTIFACTS_DIR = "models" 
# Aseguramos que el directorio exista
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

ENCODER_PATH = os.path.join(ARTIFACTS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(ARTIFACTS_DIR, "min_max_scaler.joblib")

# --- Tarea HU-005.T1: Limpieza de Datos ---

def clean_data(df):
    """
    Realiza la limpieza básica de los datos.
    - Asegura que la fecha sea datetime.
    - Elimina duplicados.
    - Maneja valores nulos (aunque nuestra tabla tiene NOT NULL).
    """
    # Convertir 'fecha' a datetime
    df['fecha'] = pd.to_datetime(df['fecha'])
    
    # Eliminar duplicados si los hubiera
    df = df.drop_duplicates()
    
    # Manejar nulos (ej. rellenar cantidad_vendida nula con 0)
    df['cantidad_vendida'] = df['cantidad_vendida'].fillna(0)
    
    # Asegurar que la cantidad sea positiva
    df = df[df['cantidad_vendida'] > 0]
    
    return df

def create_date_features(df):
    """
    Crea características de ingeniería de datos a partir de la fecha.
    """
    df['mes'] = df['fecha'].dt.month
    df['dia_del_mes'] = df['fecha'].dt.day
    df['dia_de_la_semana'] = df['fecha'].dt.dayofweek
    df['anio'] = df['fecha'].dt.year
    return df

# --- Tarea HU-005.T2: Codificación de Variables Categóricas ---

def encode_features(df, fit_encoder=False):
    """
    Codifica 'id_producto' usando LabelEncoder.
    - fit_encoder=True: Entrena un nuevo encoder y lo guarda.
    - fit_encoder=False: Carga el encoder guardado para transformar.
    """
    feature = 'id_producto'
    
    if fit_encoder:
        encoder = LabelEncoder()
        df[feature] = encoder.fit_transform(df[feature])
        # Guardar el encoder para usarlo en producción/predicción
        joblib.dump(encoder, ENCODER_PATH)
    else:
        # Cargar el encoder
        encoder = joblib.load(ENCODER_PATH)
        # Transformar los datos. 
        # Si un producto nuevo aparece, LabelEncoder dará error.
        # Una mejora futura (HU-XXX) sería manejar productos desconocidos.
        df[feature] = encoder.transform(df[feature])
        
    return df, encoder

# --- Tarea HU-005.T3: Normalización de Variables Numéricas ---

def scale_features(df, fit_scaler=False):
    """
    Escala las características numéricas usando MinMaxScaler.
    - fit_scaler=True: Entrena un nuevo scaler y lo guarda.
    - fit_scaler=False: Carga el scaler guardado para transformar.
    """
    # Definimos las características que vamos a escalar
    # 'cantidad_vendida' es nuestro OBJETIVO (Y), no una característica (X)
    features_to_scale = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']
    
    if fit_scaler:
        scaler = MinMaxScaler()
        df[features_to_scale] = scaler.fit_transform(df[features_to_scale])
        # Guardar el scaler
        joblib.dump(scaler, SCALER_PATH)
    else:
        # Cargar el scaler
        scaler = joblib.load(SCALER_PATH)
        df[features_to_scale] = scaler.transform(df[features_to_scale])
        
    return df, scaler

# --- Función Principal de Orquestación ---

def get_and_preprocess_data(for_training=True):
    """
    Orquestador principal:
    1. Obtiene datos de la BD.
    2. Limpia.
    3. Crea características de fecha.
    4. Codifica categóricas (T2).
    5. Escala numéricas (T3).
    6. Divide en Train/Test (si es para entrenamiento).
    """
    print("Iniciando preprocesamiento de datos...")
    
    # 1. Obtener datos
    engine = get_db_engine()
    if engine is None:
        return None # Salir si no hay conexión
        
    df = fetch_all_data(engine, table_name="ventas_historicas")
    if df is None or df.empty:
        print("No se encontraron datos en la base de datos.")
        return None
        
    # 2. Limpieza (T1)
    df = clean_data(df)
    
    # 3. Feature Engineering
    df = create_date_features(df)
    
    # 4. Codificación (T2)
    # Si es para entrenar, 'fit_encoder=True' crea y guarda el encoder
    df, encoder = encode_features(df, fit_encoder=for_training)
    
    # 5. Escalado (T3)
    # Si es para entrenar, 'fit_scaler=True' crea y guarda el scaler
    df, scaler = scale_features(df, fit_scaler=for_training)
    
    print("Preprocesamiento completado.")
    
    # 6. Preparar datos para el modelo
    
    # Definimos nuestras características (X) y nuestro objetivo (y)
    FEATURES = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']
    TARGET = 'cantidad_vendida'
    
    X = df[FEATURES]
    y = df[TARGET]

    if for_training:
        # Dividimos en 70% entrenamiento, 30% validación/prueba
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )
        
        print(f"Datos divididos: {len(X_train)} para entrenamiento, {len(X_test)} para prueba.")
        
        return X_train, X_test, y_train, y_test
    else:
        # Si no es para entrenar (es para predecir), devolvemos todo
        return X, y

# --- Bloque de prueba ---
if __name__ == "__main__":
    # Esto nos permite ejecutar el archivo directamente para probarlo
    # python -m backend.ml_core.preprocessing
    
    print("--- Probando el pipeline de preprocesamiento ---")
    data_split = get_and_preprocess_data(for_training=True)
    
    if data_split:
        X_train, X_test, y_train, y_test = data_split
        print("\nForma de X_train:", X_train.shape)
        print("Forma de y_train:", y_train.shape)
        print("\n--- 5 primeras filas de X_train (preprocesadas) ---")
        print(X_train.head())
        print("\n--- 5 primeras filas de y_train ---")
        print(y_train.head())
