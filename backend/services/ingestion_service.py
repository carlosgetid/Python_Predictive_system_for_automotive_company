import os
import logging
import pandas as pd
from typing import Tuple, Optional
from sqlalchemy.engine.base import Engine

# Importamos las utilidades de base de datos existentes
from backend.database.db_utils import get_db_engine, save_dataframe_to_db

# Configuración de Logging Estructurado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes para Validación de Esquema
# Definimos las columnas estrictamente requeridas para que el sistema funcione
REQUIRED_COLUMNS = {'SKU', 'Fecha Venta', 'Cantidad'}

# Mapeo de columnas: Excel/Usuario -> Base de Datos
COLUMN_MAPPING = {
    'SKU': 'id_producto',
    'Fecha Venta': 'fecha',
    'Cantidad': 'cantidad_vendida'
}

def validate_and_transform_df(df: pd.DataFrame, source_name: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Realiza la validación de esquema y transformaciones ETL (Limpieza).
    Esta función es PURA: Recibe DataFrame -> Devuelve DataFrame limpio.
    
    Args:
        df: DataFrame crudo (leído de Excel o CSV).
        source_name: Nombre del archivo para contexto en los logs.
        
    Returns:
        Tuple: (DataFrame Procesado o None, Mensaje de Error o 'Success')
    """
    # 1. Validación de Esquema (Columnas requeridas)
    actual_cols = set(df.columns)
    if not REQUIRED_COLUMNS.issubset(actual_cols):
        missing = REQUIRED_COLUMNS - actual_cols
        error_msg = f"Faltan columnas requeridas en '{source_name}': {missing}"
        logger.error(error_msg)
        return None, error_msg

    try:
        # 2. Selección y Renombrado de Columnas
        df_processed = df[list(REQUIRED_COLUMNS)].copy()
        df_processed.rename(columns=COLUMN_MAPPING, inplace=True)

        # 3. Transformación de Tipos de Datos
        # Fecha: Coerce errores a NaT (Not a Time)
        df_processed['fecha'] = pd.to_datetime(df_processed['fecha'], errors='coerce')
        
        # Cantidad: Coerce a numérico, llena nulos con 0, convierte a entero
        df_processed['cantidad_vendida'] = pd.to_numeric(
            df_processed['cantidad_vendida'], errors='coerce'
        ).fillna(0).astype(int)
        
        # SKU: Asegurar string y eliminar espacios en blanco alrededor
        df_processed['id_producto'] = df_processed['id_producto'].astype(str).str.strip()

        # 4. Limpieza de Datos (Filtrado)
        initial_rows = len(df_processed)
        
        # Eliminar filas con fechas inválidas
        df_processed.dropna(subset=['fecha'], inplace=True)
        
        # Eliminar filas con cantidades <= 0 (Devoluciones o errores)
        df_processed = df_processed[df_processed['cantidad_vendida'] > 0]
        
        clean_rows = len(df_processed)
        dropped_rows = initial_rows - clean_rows
        
        if clean_rows == 0:
            return None, "El archivo no contiene registros válidos después de la limpieza (fechas incorrectas o cantidades <= 0)."
            
        logger.info(f"Procesado '{source_name}': {clean_rows} filas válidas, {dropped_rows} descartadas.")
        return df_processed, "Success"

    except Exception as e:
        error_msg = f"Error de transformación de datos en '{source_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg

def ingest_dataframe_to_db(df: pd.DataFrame, source_name: str, engine: Optional[Engine] = None) -> Tuple[bool, str, int]:
    """
    Orquestador para Carga Manual (API) y Automática.
    Toma un DataFrame crudo, lo valida/transforma y lo guarda en BD.
    
    Args:
        df: DataFrame crudo.
        source_name: Nombre del archivo origen.
        engine: Motor SQLAlchemy opcional (inyección de dependencias).
        
    Returns:
        Tuple: (Exito: bool, Mensaje: str, Filas_Guardadas: int)
    """
    # 1. Transformación
    df_clean, msg = validate_and_transform_df(df, source_name)
    if df_clean is None:
        return False, msg, 0

    # 2. Obtener conexión a BD si no se proveyó
    if engine is None:
        engine = get_db_engine()
        if engine is None:
            return False, "Error crítico: No se pudo conectar a la base de datos.", 0

    # 3. Guardado (Carga)
    try:
        success, db_msg = save_dataframe_to_db(df_clean, "ventas_historicas", engine)
        if success:
            return True, f"Procesamiento exitoso. {db_msg}", len(df_clean)
        else:
            return False, f"Fallo al guardar en BD: {db_msg}", 0
    except Exception as e:
        logger.critical(f"Excepción no controlada guardando '{source_name}': {e}", exc_info=True)
        return False, f"Error interno: {str(e)}", 0

def process_excel_file_from_disk(file_path: str, engine: Optional[Engine] = None) -> bool:
    """
    Función específica para la HU-010 (Ingesta Automatizada desde disco).
    Lee el archivo del sistema de archivos y delega el procesamiento.
    
    Args:
        file_path: Ruta absoluta al archivo.
        
    Returns:
        bool: True si todo el proceso fue exitoso.
    """
    filename = os.path.basename(file_path)
    logger.info(f"Iniciando procesamiento de archivo en disco: {filename}")

    try:
        # Lectura específica con openpyxl para archivos .xlsx
        # Nota: 'sheet_name' debe coincidir con el formato de la empresa
        df_raw = pd.read_excel(file_path, sheet_name='Detalle', engine='openpyxl')
        
        if df_raw.empty:
            logger.warning(f"El archivo '{filename}' está vacío o la hoja 'Detalle' no tiene datos.")
            return False

        # Delegar la lógica de negocio a la función centralizada
        success, msg, _ = ingest_dataframe_to_db(df_raw, filename, engine)
        
        if not success:
            logger.error(f"Fallo en la ingesta de '{filename}': {msg}")
            
        return success

    except ValueError as ve:
        logger.error(f"Error de formato en '{filename}': Posiblemente falta la hoja 'Detalle'. Detalle: {ve}")
        return False
    except Exception as e:
        logger.critical(f"Error de sistema leyendo '{filename}': {e}", exc_info=True)
        return False