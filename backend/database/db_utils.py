import logging
import pandas as pd
from sqlalchemy import create_engine
from backend.config import DATABASE_URI
from datetime import datetime # --- NUEVO: Para registrar fecha de métricas

# Configuración de logging
# IMPORTANTE: Añadimos esta línea que no estaba en tu versión anterior
logging.basicConfig(level=logging.INFO)

def get_db_engine():
    """
    Crea y retorna un motor de SQLAlchemy.
    """
    try:
        engine = create_engine(DATABASE_URI)
        # Probar la conexión
        with engine.connect() as conn:
            logging.info("Conexión a la base de datos establecida con éxito.")
        return engine
    except Exception as e:
        logging.error(f"Error al crear el motor de base de datos: {e}")
        # En un escenario real, podríamos querer reintentar o salir
        return None

def save_dataframe_to_db(df, table_name, engine):
    """
    Guarda un DataFrame de pandas en la tabla especificada.
    Si la tabla existe, añade los datos (append).
    
    NOTA: Modificamos esta función para que acepte el 'engine' como argumento.
    """
    if engine is None:
        logging.error("No se proporcionó un motor de base de datos válido.")
        return False, "Error interno: Motor de BD no inicializado."
        
    try:
        # Usar 'to_sql' para guardar el DataFrame
        # if_exists='append' añade los datos si la tabla ya existe
        # index=False para no guardar el índice del DataFrame como una columna
        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        
        logging.info(f"Se guardaron {len(df)} filas en la tabla '{table_name}'.")
        return True, f"Datos guardados con éxito en '{table_name}'."
        
    except Exception as e:
        logging.error(f"Error al guardar datos en la BD: {e}")
        # Devolver el error para que la API pueda manejarlo
        return False, f"Error al guardar en laBD: {e}"

def fetch_all_data(engine, table_name="ventas_historicas"):
    """
    Obtiene todos los datos de una tabla y los devuelve como un DataFrame.
    """
    if engine is None:
        logging.error("No se proporcionó un motor de base de datos válido para leer.")
        return None
    
    try:
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql(query, con=engine)
        logging.info(f"Se leyeron {len(df)} filas de la tabla '{table_name}'.")
        return df
    except Exception as e:
        logging.error(f"Error al leer datos de la BD: {e}")
        return None

# --- NUEVAS FUNCIONES PARA HU-011 (Monitoreo de Métricas) ---

def save_model_metric(metrics: dict, engine):
    """
    Guarda un registro de rendimiento del modelo en la tabla 'model_metrics'.
    Recibe un diccionario con: {'model': str, 'mae': float, 'rmse': float, 'r2': float}
    """
    if engine is None:
        logging.error("No se proporcionó motor de BD para guardar métricas.")
        return False

    try:
        # 1. Preparar datos
        # Agregamos la fecha actual al diccionario de métricas
        data = metrics.copy()
        data['fecha_registro'] = datetime.now()
        
        # 2. Convertir a DataFrame
        # Pandas maneja la creación de la tabla automáticamente con to_sql
        df_metric = pd.DataFrame([data])
        
        # 3. Guardar (Append)
        df_metric.to_sql('model_metrics', con=engine, if_exists='append', index=False)
        
        logging.info(f"Métricas registradas exitosamente para: {data.get('model')}")
        return True

    except Exception as e:
        logging.error(f"Error al guardar métricas en BD: {e}")
        return False

def get_model_metrics_history(engine):
    """
    Recupera todo el historial de métricas para visualizar su evolución.
    """
    if engine is None:
        return pd.DataFrame() # Retorna vacío si no hay conexión
    
    try:
        # Ordenamos por fecha descendente para ver lo más reciente primero
        query = "SELECT * FROM model_metrics ORDER BY fecha_registro DESC"
        df = pd.read_sql(query, con=engine)
        return df
    except Exception as e:
        # Si la tabla no existe (primer uso), no es un error crítico, retornamos vacío
        logging.warning(f"No se pudo leer historial de métricas (¿Tabla vacía?): {e}")
        return pd.DataFrame()