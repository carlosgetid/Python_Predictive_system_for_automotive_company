import pandas as pd
from sqlalchemy import create_engine, text
from backend.config import DATABASE_URI

# Creamos un "motor" de conexión usando SQLAlchemy
# Este motor manejará las conexiones a la BD de forma eficiente
try:
    engine = create_engine(DATABASE_URI)
except ImportError:
    raise ImportError("Asegúrate de haber instalado 'SQLAlchemy' y 'mysql-connector-python'")
except Exception as e:
    print(f"Error al crear el engine de la BD: {e}")
    engine = None

def test_db_connection():
    """Intenta conectar a la BD y ejecutar una consulta simple."""
    if engine is None:
        return False, "El motor de la BD no se inicializó."
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return True, "Conexión a la BD exitosa."
    except Exception as e:
        return False, f"Error al conectar a la BD: {e}"

def save_dataframe_to_db(df, table_name):
    """
    Guarda un DataFrame de pandas en la tabla especificada.
    
    Args:
        df (pd.DataFrame): El dataframe a guardar.
        table_name (str): El nombre de la tabla de destino.
    """
    if engine is None:
        raise ConnectionError("No se pudo conectar a la base de datos (engine no inicializado).")
        
    try:
        # Tarea HU-001.T5: Crear la lógica para guardar los datos validados
        # 'if_exists='append'' añade los datos sin borrar los existentes.
        # 'index=False' evita que pandas guarde el índice del dataframe como una columna.
        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        
        # Devolvemos un resumen de los datos guardados
        summary = {
            "filas_guardadas": len(df),
            "primera_fecha": str(df['fecha'].min()),
            "ultima_fecha": str(df['fecha'].max())
        }
        return summary

    except Exception as e:
        # Manejamos errores comunes, como que la tabla no exista
        raise Exception(f"Error al guardar en la BD: {e}")

