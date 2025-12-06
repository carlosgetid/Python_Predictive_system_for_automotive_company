import logging
from sqlalchemy import text
from werkzeug.security import check_password_hash
from backend.database.db_utils import get_db_engine

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def authenticate_user(username, password):
    """
    Verifica las credenciales del usuario contra la base de datos.
    
    Args:
        username (str): Nombre de usuario proporcionado.
        password (str): Contraseña en texto plano.
        
    Returns:
        dict: Datos del usuario (id, nombre, rol) si las credenciales son válidas.
        None: Si la autenticación falla (usuario no existe o contraseña incorrecta).
    """
    engine = get_db_engine()
    if not engine:
        logger.error("No se pudo conectar a la base de datos para autenticación.")
        return None

    try:
        with engine.connect() as conn:
            # 1. Buscar el usuario por username
            # Seleccionamos explícitamente las columnas para evitar errores de índice
            query = text("SELECT id, username, password_hash, nombre, rol FROM usuarios WHERE username = :u")
            result = conn.execute(query, {"u": username}).fetchone()

            if result:
                # SQLAlchemy devuelve un objeto Row, accedemos por índices según el SELECT
                db_id = result[0]
                db_username = result[1]
                db_hash = result[2]
                db_nombre = result[3]
                db_rol = result[4]

                # 2. Verificar la contraseña (Hash vs Texto Plano)
                if check_password_hash(db_hash, password):
                    logger.info(f"✅ Autenticación exitosa para usuario: {username} ({db_rol})")
                    
                    # Retornamos solo la información segura (sin el hash)
                    return {
                        "id": db_id,
                        "username": db_username,
                        "nombre": db_nombre,
                        "rol": db_rol
                    }
                else:
                    logger.warning(f"❌ Contraseña incorrecta para usuario: {username}")
                    return None
            else:
                logger.warning(f"⚠️ Usuario no encontrado: {username}")
                return None

    except Exception as e:
        logger.error(f"Error crítico en servicio de autenticación: {e}", exc_info=True)
        return None