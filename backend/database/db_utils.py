import logging
import pandas as pd
from sqlalchemy import create_engine, text
from backend.config import DATABASE_URI
from datetime import datetime
import uuid

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

def initialize_db(engine):
    """Crea las tablas necesarias si no existen."""
    if engine is None: return
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alertas_inventario (
                    id VARCHAR(36) PRIMARY KEY,
                    sku VARCHAR(255) NOT NULL,
                    tipo_alerta VARCHAR(50) NOT NULL,
                    mensaje TEXT,
                    fecha_proyeccion DATE,
                    estado VARCHAR(50) DEFAULT 'PENDIENTE',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS configuracion_sistema (
                    id SERIAL PRIMARY KEY,
                    smtp_host VARCHAR(255) DEFAULT 'smtp.gmail.com',
                    smtp_port INT DEFAULT 587,
                    smtp_user VARCHAR(255) DEFAULT '',
                    smtp_pass VARCHAR(255) DEFAULT '',
                    email_remitente VARCHAR(255) DEFAULT 'alertas@predictivo.auto',
                    email_destinatario_alertas VARCHAR(255) DEFAULT ''
                );
            """))
            
            # Insert default row if empty
            result = conn.execute(text("SELECT COUNT(*) FROM configuracion_sistema")).scalar()
            if result == 0:
                conn.execute(text("""
                    INSERT INTO configuracion_sistema (smtp_host, smtp_port) VALUES ('smtp.gmail.com', 587)
                """))
                
            logger.info("Tablas de sistema verificadas/creadas con éxito.")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")

def get_db_engine_and_init():
    engine = get_db_engine()
    initialize_db(engine)
    return engine

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

# --- FUNCIONES DE ALERTAS (HU-007) ---

def insert_or_update_alert(sku: str, tipo_alerta: str, mensaje: str, fecha_proyeccion: str, engine):
    """
    Inserta una nueva alerta o actualiza una existente (si es del mismo tipo, SKU y sigue PENDIENTE).
    Evita duplicar alertas PENDIENTE para el mismo SKU.
    """
    if engine is None: return False
    
    try:
        with engine.begin() as conn:
            # Buscar si ya existe una alerta pendiente para este SKU y tipo
            query_check = text("""
                SELECT id FROM alertas_inventario 
                WHERE sku = :sku AND tipo_alerta = :tipo AND estado = 'PENDIENTE'
            """)
            result = conn.execute(query_check, {"sku": sku, "tipo": tipo_alerta}).fetchone()
            
            if result:
                # Actualizar la alerta existente
                query_update = text("""
                    UPDATE alertas_inventario 
                    SET mensaje = :mensaje, fecha_proyeccion = :fecha_proy, creado_en = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                conn.execute(query_update, {
                    "mensaje": mensaje, 
                    "fecha_proy": fecha_proyeccion, 
                    "id": result[0]
                })
                logger.info(f"Alerta actualizada para SKU: {sku} (Tipo: {tipo_alerta})")
            else:
                # Insertar nueva alerta
                alert_id = str(uuid.uuid4())
                query_insert = text("""
                    INSERT INTO alertas_inventario (id, sku, tipo_alerta, mensaje, fecha_proyeccion, estado)
                    VALUES (:id, :sku, :tipo, :mensaje, :fecha_proy, 'PENDIENTE')
                """)
                conn.execute(query_insert, {
                    "id": alert_id,
                    "sku": sku,
                    "tipo": tipo_alerta,
                    "mensaje": mensaje,
                    "fecha_proy": fecha_proyeccion
                })
                logger.info(f"Nueva alerta creada para SKU: {sku} (Tipo: {tipo_alerta})")
        return True
    except Exception as e:
        logger.error(f"Error al procesar alerta para SKU {sku}: {e}", exc_info=True)
        return False

def get_active_alerts(engine):
    """Retorna las alertas con estado PENDIENTE."""
    if engine is None: return []
    try:
        query = text("""
            SELECT id, sku, tipo_alerta, mensaje, fecha_proyeccion, estado, creado_en 
            FROM alertas_inventario 
            WHERE estado = 'PENDIENTE' 
            ORDER BY creado_en DESC
        """)
        with engine.connect() as conn:
            result = conn.execute(query)
            # Convert row objects to dict
            alerts = [dict(row._mapping) for row in result]
            # Convert datetime to string for JSON serialization
            for alert in alerts:
                if 'fecha_proyeccion' in alert and alert['fecha_proyeccion']:
                    alert['fecha_proyeccion'] = str(alert['fecha_proyeccion'])
                if 'creado_en' in alert and alert['creado_en']:
                    alert['creado_en'] = str(alert['creado_en'])
            return alerts
    except Exception as e:
        logger.error(f"Error al obtener alertas activas: {e}", exc_info=True)
        return []

def update_alert_status(alert_id: str, status: str, engine):
    """Cambia el estado de una alerta (e.g., CONFIRMADA, DESCARTADA)."""
    if engine is None: return False
    valid_statuses = ['PENDIENTE', 'CONFIRMADA', 'DESCARTADA']
    if status not in valid_statuses:
        logger.error(f"Estado de alerta inválido: {status}")
        return False
        
    try:
        query = text("""
            UPDATE alertas_inventario 
            SET estado = :status 
            WHERE id = :id
        """)
        with engine.begin() as conn:
            result = conn.execute(query, {"status": status, "id": alert_id})
            if result.rowcount > 0:
                logger.info(f"Estado de alerta {alert_id} actualizado a {status}")
                return True
            else:
                logger.warning(f"No se encontró la alerta con id {alert_id}")
                return False
    except Exception as e:
        logger.error(f"Error al actualizar estado de alerta {alert_id}: {e}", exc_info=True)
        return False

# --- FUNCIONES DE CONFIGURACIÓN DE SISTEMA ---

def get_config_params(engine=None):
    """Obtiene los parámetros de configuración de correo."""
    if engine is None: 
        engine = get_db_engine()
    if engine is None: return {}
    
    try:
        query = text("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, email_remitente, email_destinatario_alertas FROM configuracion_sistema LIMIT 1")
        with engine.connect() as conn:
            result = conn.execute(query).fetchone()
            if result:
                return dict(result._mapping)
            else:
                return {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_user": "",
                    "smtp_pass": "",
                    "email_remitente": "alertas@predictivo.auto",
                    "email_destinatario_alertas": ""
                }
    except Exception as e:
        logger.error(f"Error al obtener configuración: {e}")
        return {}

def update_config_params(data: dict, engine=None):
    """Actualiza los parámetros de configuración."""
    if engine is None: 
        engine = get_db_engine()
    if engine is None: return False
    
    try:
        with engine.begin() as conn:
            # Asumimos que siempre hay una fila (id=1)
            query = text("""
                UPDATE configuracion_sistema 
                SET smtp_host = :smtp_host,
                    smtp_port = :smtp_port,
                    smtp_user = :smtp_user,
                    smtp_pass = :smtp_pass,
                    email_remitente = :email_remitente,
                    email_destinatario_alertas = :email_destinatario_alertas
            """)
            conn.execute(query, {
                "smtp_host": data.get("smtp_host", "smtp.gmail.com"),
                "smtp_port": data.get("smtp_port", 587),
                "smtp_user": data.get("smtp_user", ""),
                "smtp_pass": data.get("smtp_pass", ""),
                "email_remitente": data.get("email_remitente", "alertas@predictivo.auto"),
                "email_destinatario_alertas": data.get("email_destinatario_alertas", "")
            })
            logger.info("Configuración del sistema actualizada con éxito.")
            return True
    except Exception as e:
        logger.error(f"Error al actualizar configuración: {e}", exc_info=True)
        return False