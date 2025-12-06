import sys
import os
import logging
from sqlalchemy import text
from werkzeug.security import generate_password_hash

# --- Configuración de Rutas ---
# Agregamos la raíz del proyecto al path para poder importar 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db_utils import get_db_engine

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def seed_users():
    """
    Crea la tabla de usuarios e inserta los datos iniciales con contraseñas hasheadas.
    """
    engine = get_db_engine()
    if not engine:
        logger.error("No se pudo conectar a la base de datos.")
        sys.exit(1)

    # Datos de los Usuarios (Basados en tus perfiles)
    # Definimos una contraseña inicial estándar para facilitar las pruebas
    default_password = "teo123" 
    
    users_data = [
        {
            "username": "lfernandez",
            "nombre": "Luis Fernández",
            "rol": "Analista Logística",
            "password": default_password
        },
        {
            "username": "storres",
            "nombre": "Sofía Torres",
            "rol": "Jefa Almacén",
            "password": default_password
        },
        {
            "username": "jmendoza",
            "nombre": "Javier Mendoza",
            "rol": "Gerente Administración",
            "password": default_password
        },
        {
            "username": "aquispe",
            "nombre": "Ana Quispe",
            "rol": "Vendedora",
            "password": default_password
        },
        {
            "username": "rsolano",
            "nombre": "Ricardo Solano",
            "rol": "Gerente General",
            "password": default_password
        }
    ]

    try:
        with engine.connect() as conn:
            # 1. Crear Tabla de Usuarios (si no existe)
            logger.info("Creando/Verificando tabla 'usuarios'...")
            
            ddl_usuarios = text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                rol VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute(ddl_usuarios)
            
            # 2. Limpiar usuarios anteriores para evitar duplicados en pruebas
            logger.info("Limpiando tabla usuarios para carga limpia...")
            conn.execute(text("TRUNCATE TABLE usuarios;"))
            
            # 3. Insertar Usuarios
            logger.info("Insertando usuarios semilla...")
            
            for user in users_data:
                # Hashing de la contraseña (Seguridad)
                # pbkdf2:sha256 es el método por defecto robusto de Werkzeug
                p_hash = generate_password_hash(user["password"])
                
                # Query de inserción
                insert_query = text("""
                INSERT INTO usuarios (username, password_hash, nombre, rol)
                VALUES (:u, :p, :n, :r)
                """)
                
                conn.execute(insert_query, {
                    "u": user["username"],
                    "p": p_hash,
                    "n": user["nombre"],
                    "r": user["rol"]
                })
                
                logger.info(f"Usuario creado: {user['username']} - Rol: {user['rol']}")
            
            conn.commit()
            logger.info("✅ Carga de usuarios completada exitosamente.")
            logger.info(f"ℹ️  La contraseña para todos los usuarios es: '{default_password}'")

    except Exception as e:
        logger.error(f"❌ Error crítico en seeding de usuarios: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    seed_users()