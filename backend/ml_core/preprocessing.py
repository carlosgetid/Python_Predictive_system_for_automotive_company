import pandas as pd
import numpy as np
# ¡Volvemos a LabelEncoder!
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import os
import logging

# --- Importar lógica de BD ---
from backend.database.db_utils import get_db_engine, fetch_all_data

# --- Constantes (Revertidas a MVP) ---
ARTIFACTS_DIR = "models"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Nombres originales de los artefactos
ENCODER_PATH = os.path.join(ARTIFACTS_DIR, "label_encoder_producto.joblib")
SCALER_PATH = os.path.join(ARTIFACTS_DIR, "min_max_scaler.joblib")

# --- Tarea HU-005.T1: Limpieza de Datos (Revertida a MVP) ---
def clean_data(df):
    """
    Realiza la limpieza básica para los datos de 'ventas_historicas'.
    - Asegura que la fecha sea datetime.
    - Elimina duplicados.
    - Asegura que cantidad_vendida sea positiva.
    """
    try:
        # Intenta convertir la columna 'fecha', maneja diferentes formatos si es necesario
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        # Elimina filas donde la fecha no pudo ser convertida
        df.dropna(subset=['fecha'], inplace=True)
        if df.empty:
             logging.warning("No quedan datos después de validar el formato de fecha.")
             # Devolver df vacío en lugar de lanzar error, permite que el flujo continúe y reporte fallo más adelante si es necesario
             return df
    except Exception as e:
        logging.error(f"Error inesperado al convertir 'fecha' a datetime en clean_data: {e}")
        # Considerar lanzar un error más específico o devolver df vacío
        raise ValueError("Error procesando las fechas en la base de datos.") from e

    df = df.drop_duplicates()
    # Asegura que cantidad_vendida sea numérico, maneja errores y nulos, luego convierte a int
    df['cantidad_vendida'] = pd.to_numeric(df['cantidad_vendida'], errors='coerce').fillna(0).astype(int)
    # Mantener solo ventas positivas
    df = df[df['cantidad_vendida'] > 0]
    return df

# --- Tarea HU-005.T?: Feature Engineering (Reincorporada) ---
def create_date_features(df):
    """
    Crea características de ingeniería de datos a partir de la fecha.
    """
    df['mes'] = df['fecha'].dt.month
    df['dia_del_mes'] = df['fecha'].dt.day
    df['dia_de_la_semana'] = df['fecha'].dt.dayofweek # Lunes=0, Domingo=6
    df['anio'] = df['fecha'].dt.year
    return df

# --- Tarea HU-005.T2: Codificación (Revertida a MVP) ---
def encode_features(df, fit_encoder=False):
    """
    Codifica 'id_producto' usando LabelEncoder.
    - fit_encoder=True: Entrena un nuevo encoder y lo guarda.
    - fit_encoder=False: Carga el encoder guardado para transformar. Maneja desconocidos.
    """
    feature = 'id_producto'
    try:
        # Asegurarse que la columna es string antes de cualquier operación
        df[feature] = df[feature].astype(str)

        if fit_encoder:
            logging.info(f"Ajustando nuevo LabelEncoder para '{feature}'...")
            encoder = LabelEncoder()
            df[feature] = encoder.fit_transform(df[feature])
            joblib.dump(encoder, ENCODER_PATH)
            logging.info(f"Encoder guardado en: {ENCODER_PATH}")
        else:
            if not os.path.exists(ENCODER_PATH):
                logging.error(f"Error: No se encontró el encoder en {ENCODER_PATH}. Ejecuta el entrenamiento primero.")
                # Devolver None indica un fallo crítico
                return None, None
            encoder = joblib.load(ENCODER_PATH)
            # Manejar productos desconocidos durante la predicción
            known_labels = set(encoder.classes_) # Usar set para búsqueda rápida
            # Aplicar transformación, asignar -1 a desconocidos
            df[feature] = df[feature].apply(lambda x: encoder.transform([x])[0] if x in known_labels else -1)

            # Contar y potencialmente filtrar desconocidos
            unknown_count = (df[feature] == -1).sum()
            if unknown_count > 0:
                logging.warning(f"Se encontraron {unknown_count} instancias de productos desconocidos (no vistos en entrenamiento). Serán excluidos.")
                df = df[df[feature] != -1].copy() # Usar .copy() para evitar SettingWithCopyWarning
                if df.empty:
                    logging.warning("Todos los productos eran desconocidos, no quedan datos.")
                    # Devolver df vacío pero encoder cargado
                    return df, encoder

        return df, encoder
    except Exception as e:
        logging.error(f"Error durante la codificación de '{feature}': {e}", exc_info=True)
        # Devolver None indica un fallo crítico
        return None, None

# --- Tarea HU-005.T3: Normalización (Revertida a MVP) ---
def scale_features(df, fit_scaler=False):
    """
    Escala las características numéricas del MVP usando MinMaxScaler.
    """
    # Features del MVP: id_producto codificado + features de fecha
    features_to_scale = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']

    # Verificar que las columnas existan antes de intentar usarlas
    missing_cols = [col for col in features_to_scale if col not in df.columns]
    if missing_cols:
        logging.error(f"Faltan columnas requeridas para escalar: {missing_cols}. DataFrame columns: {df.columns.tolist()}")
        return None, None # Fallo crítico si faltan columnas

    # Asegurarse de que no haya datos no numéricos o infinitos antes de escalar
    for col in features_to_scale:
         # Intentar convertir a numérico, los errores se vuelven NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
         # Reemplazar infinitos (si los hubiera) por NaN
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Contar NaNs introducidos o existentes
    nan_rows_before = df.isnull().any(axis=1).sum()
    if nan_rows_before > 0:
        logging.warning(f"Se encontraron {nan_rows_before} filas con valores no numéricos/infinitos en las columnas a escalar. Estas filas serán eliminadas.")
        df.dropna(subset=features_to_scale, inplace=True)
        if df.empty:
             logging.error("No quedan datos después de eliminar filas con valores inválidos para el escalado.")
             return None, None # Fallo si no quedan datos

    try:
        if fit_scaler:
            logging.info(f"Ajustando nuevo MinMaxScaler para {features_to_scale}...")
            scaler = MinMaxScaler()
            # fit_transform asume que los datos ya son numéricos y finitos
            df[features_to_scale] = scaler.fit_transform(df[features_to_scale])
            joblib.dump(scaler, SCALER_PATH)
            logging.info(f"Scaler guardado en: {SCALER_PATH}")
        else:
            if not os.path.exists(SCALER_PATH):
                logging.error(f"Error: No se encontró el scaler en {SCALER_PATH}. Ejecuta el entrenamiento primero.")
                return None, None # Fallo crítico
            scaler = joblib.load(SCALER_PATH)
            # transform asume datos numéricos y finitos
            df[features_to_scale] = scaler.transform(df[features_to_scale])

        return df, scaler
    except Exception as e:
        logging.error(f"Error durante el escalado: {e}", exc_info=True)
        return None, None # Fallo crítico

# --- Función Principal de Orquestación (Revertida a MVP) ---
def get_and_preprocess_data(for_training=True):
    """
    Orquestador principal (MVP):
    1. Obtiene datos de 'ventas_historicas'.
    2. Limpia.
    3. Crea características de fecha.
    4. Codifica id_producto (T2).
    5. Escala numéricas (T3).
    6. Divide en Train/Test.
    """
    logging.info("Iniciando preprocesamiento (lógica MVP)...")

    # 1. Obtener datos
    engine = get_db_engine()
    if engine is None: return None
    # Asegúrate que la tabla correcta existe
    try:
        df = fetch_all_data(engine, table_name="ventas_historicas")
    except Exception as e:
        logging.error(f"Error al leer de la base de datos (tabla 'ventas_historicas'): {e}")
        return None

    if df is None or df.empty:
        logging.error("No se encontraron datos en 'ventas_historicas' o la tabla está vacía.")
        return None

    # 2. Limpieza (T1)
    try:
        df = clean_data(df)
        if df.empty:
            logging.warning("No quedan datos después de la limpieza inicial.")
            return None # No se puede continuar sin datos
    except ValueError as e: # Captura error de formato de fecha u otros de limpieza
         logging.error(f"Error en limpieza de datos: {e}")
         return None


    # 3. Feature Engineering
    df = create_date_features(df)

    # 4. Codificación (T2)
    df, encoder = encode_features(df, fit_encoder=for_training)
    # Verificar si encode_features falló
    if encoder is None and df is None:
        logging.error("Fallo crítico en la codificación.")
        return None
    # Verificar si no quedan datos después de filtrar desconocidos (solo aplica si for_training=False)
    if df.empty and not for_training:
        logging.warning("No quedan datos después de la codificación (posiblemente todos eran productos desconocidos).")
        # En predicción, podríamos necesitar devolver X, y vacíos
        X = pd.DataFrame(columns=['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio'])
        y = pd.Series(name='cantidad_vendida', dtype=int)
        return X, y
    elif df.empty and for_training:
         logging.error("No quedan datos para entrenar después de la codificación.")
         return None


    # 5. Escalado (T3)
    df, scaler = scale_features(df, fit_scaler=for_training)
    # Verificar si scale_features falló
    if scaler is None and df is None:
        logging.error("Fallo crítico en el escalado.")
        return None
    # Verificar si no quedan datos después de eliminar NaNs
    if df.empty:
        logging.error("No quedan datos válidos después del escalado.")
        if not for_training: # Devolver vacío para predicción
            X = pd.DataFrame(columns=['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio'])
            y = pd.Series(name='cantidad_vendida', dtype=int)
            return X, y
        else: # Error si no hay datos para entrenar
            return None


    logging.info("Preprocesamiento (lógica MVP) completado.")

    # 6. Preparar datos para el modelo (MVP)
    FEATURES = ['id_producto', 'mes', 'dia_del_mes', 'dia_de_la_semana', 'anio']
    TARGET = 'cantidad_vendida'

    # Doble chequeo de columnas antes de la división
    if not all(col in df.columns for col in FEATURES):
        logging.error(f"Faltan columnas FEATURES ('{FEATURES}') justo antes de dividir. Columnas disponibles: {df.columns.tolist()}")
        return None
    if TARGET not in df.columns:
        logging.error(f"Falta la columna TARGET ('{TARGET}') justo antes de dividir.")
        return None


    X = df[FEATURES]
    y = df[TARGET]

    if for_training:
        if len(X) < 2: # Necesitamos al menos 2 muestras para dividir
            logging.error(f"No hay suficientes datos ({len(X)} filas) para dividir en entrenamiento y prueba.")
            return None

        # --- CORRECCIÓN PARA EL ERROR DE ESTRATIFICACIÓN ---
        # Calcular cuántas veces aparece cada producto
        counts = X['id_producto'].value_counts()
        # Verificar si algún producto aparece menos de 2 veces
        can_stratify = (counts >= 2).all() if X['id_producto'].nunique() > 1 else False

        stratify_option = None
        if can_stratify:
            stratify_option = X['id_producto']
            logging.info("Todos los productos tienen al menos 2 muestras. Se usará estratificación.")
        else:
            logging.warning("Algunos productos tienen menos de 2 muestras. La división train/test NO será estratificada.")

        # test_size dinámico, asegurando al menos 1 muestra para test si es posible
        # Usar un tamaño fijo como 0.2 o 0.3 es generalmente preferible si hay suficientes datos
        test_size = 0.2 # Usaremos 20% para prueba

        # Asegurarse de que el tamaño de prueba no sea cero o negativo
        if int(len(X) * test_size) < 1 and len(X) >= 2:
            test_size = 1 / len(X) # Asegurar al menos una muestra en test si len(X) >= 2

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=42,
                stratify=stratify_option # Usar la variable que decidimos
            )
            logging.info(f"Datos divididos: {len(X_train)} entrenamiento, {len(X_test)} prueba.")
            return X_train, X_test, y_train, y_test
        except Exception as e:
             logging.error(f"Error durante train_test_split: {e}", exc_info=True)
             return None

    else:
        # Para predicción, devolvemos todo X e y (ya preprocesados)
        return X, y

# --- Bloque de prueba ---
if __name__ == "__main__":
    # Configurar logging para ver los mensajes INFO y WARNING
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    print("--- Probando el pipeline de preprocesamiento (lógica MVP) ---")

    # for_training=True para generar los artefactos del MVP
    data_split = get_and_preprocess_data(for_training=True)

    if data_split:
        X_train, X_test, y_train, y_test = data_split
        print("\nForma de X_train:", X_train.shape)
        print("Forma de y_train:", y_train.shape)
        # Verificar si X_train no está vacío antes de llamar a head()
        if not X_train.empty:
            print("\n--- 5 primeras filas de X_train (preprocesadas) ---")
            print(X_train.head())
        else:
            print("\nX_train está vacío después de la división.")
        # Verificar si y_train no está vacío antes de llamar a head()
        if not y_train.empty:
            print("\n--- 5 primeras filas de y_train (Cantidad) ---")
            print(y_train.head())
        else:
            print("\ny_train está vacío después de la división.")
    else:
        print("\nEl preprocesamiento falló o no generó datos.")

