import logging
import pandas as pd
from sqlalchemy import create_engine
from backend.config import DATABASE_URI
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- PATRÓN SINGLETON ---
# Variable global para almacenar el motor y no recrearlo constantemente
_db_engine = None

def get_db_engine():
    """
    Retorna el motor de base de datos existente o crea uno nuevo si no existe.
    Implementa patrón Singleton para estabilidad y rendimiento.
    """
    global _db_engine
    
    # 1. Si ya existe, devolverlo inmediatamente (Rápido y Seguro)
    if _db_engine is not None:
        return _db_engine

    # 2. Si no existe, crearlo (Solo ocurre una vez al arrancar)
    try:
        print("🔌 Intentando conectar a la Base de Datos (Inicialización)...")
        # pool_pre_ping=True ayuda a recuperar conexiones perdidas sin crashear
        engine = create_engine(DATABASE_URI, pool_pre_ping=True)
        
        # Prueba de conexión inicial
        with engine.connect() as conn:
            print("✅ ¡Conexión a PostgreSQL exitosa!")
            logger.info("Conexión a la base de datos establecida con éxito.")
        
        # Guardamos el motor en la variable global
        _db_engine = engine
        return _db_engine

    except Exception as e:
        print(f"❌ ERROR CRÍTICO DE CONEXIÓN: {e}")
        logger.error(f"Error al crear el motor de base de datos: {e}", exc_info=True)
        return None

def save_dataframe_to_db(df, table_name, engine):
    """
    Guarda un DataFrame de pandas en la tabla especificada.
    """
    if engine is None:
        logger.error("No se proporcionó un motor de base de datos válido.")
        return False, "Error interno: Motor de BD no inicializado."
        
    try:
        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        logger.info(f"Se guardaron {len(df)} filas en la tabla '{table_name}'.")
        return True, f"Datos guardados con éxito en '{table_name}'."
        
    except Exception as e:
        logger.error(f"Error al guardar datos en la BD: {e}")
        return False, f"Error al guardar en la BD: {e}"

def fetch_all_data(engine, table_name="ventas_detalle"): # <-- CAMBIO 1: Nombre de tabla actualizado
    """
    Obtiene todos los datos de una tabla.
    """
    if engine is None:
        return None
    
    try:
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql(query, con=engine)
        return df
    except Exception as e:
        logger.error(f"Error al leer datos de la BD: {e}")
        return None

# --- FUNCIONES DE MÉTRICAS ---

def save_model_metric(metrics: dict, engine):
    if engine is None: return False
    try:
        data = metrics.copy()
        data['fecha_registro'] = datetime.now()
        # <-- CAMBIO 2: Tabla 'entrenamiento'
        pd.DataFrame([data]).to_sql('entrenamiento', con=engine, if_exists='append', index=False)
        return True
    except Exception as e:
        logger.error(f"Error al guardar métricas: {e}")
        return False

def get_model_metrics_history(engine):
    if engine is None: return pd.DataFrame()
    try:
        # <-- CAMBIO 3: Tabla 'entrenamiento'
        query = "SELECT * FROM entrenamiento ORDER BY fecha_registro DESC"
        return pd.read_sql(query, con=engine)
    except Exception as e:
        logger.warning(f"No se pudo leer historial de métricas: {e}")
        return pd.DataFrame()