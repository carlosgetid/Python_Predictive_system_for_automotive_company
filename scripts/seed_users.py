import sys
import os
import logging
from sqlalchemy import text
from werkzeug.security import generate_password_hash

# --- Configuración de Rutas ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db_utils import get_db_engine

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def seed_users():
    """
    Crea la tabla de usuarios (Sintaxis PostgreSQL) e inserta datos iniciales.
    """
    engine = get_db_engine()
    if not engine:
        logger.error("No se pudo conectar a la base de datos.")
        sys.exit(1)

    # Datos de los Usuarios
    default_password = "teo123"
    users_data = [
        {"username": "lfernandez", "nombre": "Luis Fernández", "rol": "Analista Logística", "password": default_password},
        {"username": "storres", "nombre": "Sofía Torres", "rol": "Jefa Almacén", "password": default_password},
        {"username": "jmendoza", "nombre": "Javier Mendoza", "rol": "Gerente Administración", "password": default_password},
        {"username": "aquispe", "nombre": "Ana Quispe", "rol": "Vendedora", "password": default_password},
        {"username": "rsolano", "nombre": "Ricardo Solano", "rol": "Gerente General", "password": default_password}
    ]

    try:
        with engine.connect() as conn:
            logger.info("Creando/Verificando tabla 'usuarios'...")
            
            # --- CAMBIO CRÍTICO: Sintaxis PostgreSQL ---
            # 1. Usamos GENERATED ALWAYS AS IDENTITY en lugar de AUTO_INCREMENT
            # 2. TIMESTAMP sin configuración especial (Postgres lo maneja bien)
            ddl_usuarios = text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                rol VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute(ddl_usuarios)
            
            # --- CAMBIO CRÍTICO: Limpieza ---
            logger.info("Limpiando tabla usuarios para carga limpia...")
            # En Postgres usamos TRUNCATE con RESTART IDENTITY para reiniciar IDs
            conn.execute(text("TRUNCATE TABLE usuarios RESTART IDENTITY CASCADE;"))
            
            logger.info("Insertando usuarios semilla...")
            
            query_insert = text("""
                INSERT INTO usuarios (username, password_hash, nombre, rol)
                VALUES (:u, :p, :n, :r)
            """)

            for user in users_data:
                p_hash = generate_password_hash(user["password"])
                conn.execute(query_insert, {
                    "u": user["username"],
                    "p": p_hash,
                    "n": user["nombre"],
                    "r": user["rol"]
                })
                logger.info(f"Usuario creado: {user['username']}")
            
            conn.commit()
            logger.info("✅ Carga de usuarios completada exitosamente.")

    except Exception as e:
        logger.error(f"❌ Error crítico en seeding de usuarios: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    seed_users()