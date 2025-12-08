import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database.db_utils import get_db_engine

def reset_tables():
    """Trunca las tablas del sistema (Versión PostgreSQL)."""
    engine = get_db_engine()
    if not engine:
        print("Error: No se pudo conectar a la base de datos.")
        sys.exit(1)

    try:
        with engine.connect() as conn:
            print("🗑️  Iniciando limpieza de tablas...")
            
            # --- CAMBIO CRÍTICO: Sintaxis PostgreSQL ---
            # Usamos CASCADE para borrar datos dependientes y RESTART IDENTITY para los IDs
            conn.execute(text("TRUNCATE TABLE ventas_historicas RESTART IDENTITY CASCADE;"))
            
            # Nota: 'model_metrics' se crea automáticamente al entrenar, 
            # pero si existe, la limpiamos. Usamos un bloque try/except por si no existe aún.
            try:
                conn.execute(text("TRUNCATE TABLE model_metrics RESTART IDENTITY CASCADE;"))
            except Exception:
                print("ℹ️  Tabla model_metrics no existía (no pasa nada).")

            conn.commit()
            print("✅ Tablas limpiadas exitosamente.")
            
    except Exception as e:
        print(f"❌ Error crítico limpiando tablas: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_tables()