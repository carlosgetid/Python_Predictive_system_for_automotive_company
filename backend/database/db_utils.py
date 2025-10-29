import logging
import pandas as pd
from sqlalchemy import create_engine
from backend.config import DATABASE_URI

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

