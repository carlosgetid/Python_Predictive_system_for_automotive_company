import sys
import os
from sqlalchemy import text

# --- Configuración de Rutas ---
# Agregamos la raíz del proyecto al path para poder importar 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db_utils import get_db_engine

def reset_tables():
    """Trunca las tablas del sistema para reiniciar el entorno."""
    engine = get_db_engine()
    if not engine:
        print("Error: No se pudo conectar a la base de datos.")
        sys.exit(1)

    try:
        with engine.connect() as conn:
            # Desactivar checks de llaves foráneas temporalmente si fuera necesario
            # conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            
            print("🗑️  Truncando tabla 'ventas_historicas'...")
            conn.execute(text("TRUNCATE TABLE ventas_historicas;"))
            
            print("🗑️  Truncando tabla 'model_metrics'...")
            conn.execute(text("TRUNCATE TABLE model_metrics;"))
            
            # Reactivar checks
            # conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            
            conn.commit()
            print("✅ Tablas limpiadas exitosamente.")
            
    except Exception as e:
        print(f"❌ Error crítico limpiando tablas: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_tables()