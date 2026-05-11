import logging
import os  # <-- AÑADIDO: Necesario para leer variables de entorno en Render
from flask import Flask
from flask_cors import CORS
# ELIMINADO: from backend.config import DEBUG_MODE

# Importamos el Blueprint que contiene TODAS nuestras rutas (/upload, /predict, /history)
from backend.api.routes import api_bp

# Configurar logging (para que se vea en la consola)
logging.basicConfig(level=logging.INFO)

def create_app():
    """
    Fábrica de la aplicación Flask.
    """
    app = Flask(__name__)
    CORS(app) # Habilita CORS para todas las rutas

    # Registrar el Blueprint de la API
    app.register_blueprint(api_bp, url_prefix='/')

    @app.route('/health')
    def health_check():
        """
        Un endpoint simple para verificar que el servidor está vivo.
        """
        logging.info("Health check endpoint fue llamado.")
        return {"status": "ok"}, 200

    # --- Sincronización de intervalos de pipeline al arrancar ---
    # Esto garantiza que los archivos .interval reflejen los valores de la BD
    # incluso si Render reinició el dyno (sistema de archivos efímero).
    with app.app_context():
        try:
            from backend.database.db_utils import get_db_engine_and_init, get_pipeline_intervals
            from backend.api.routes import SCRIPTS_DIR, _write_interval_minutes
            engine = get_db_engine_and_init()
            if engine:
                intervals = get_pipeline_intervals(engine)
                for worker_id, minutes in intervals.items():
                    try:
                        _write_interval_minutes(worker_id, minutes)
                        logging.info(f"[Startup] Intervalo de '{worker_id}' sincronizado: {minutes} min")
                    except Exception as sync_err:
                        logging.warning(f"[Startup] No se pudo sincronizar intervalo de '{worker_id}': {sync_err}")
        except Exception as e:
            logging.warning(f"[Startup] No se pudieron sincronizar intervalos de pipeline: {e}")

    return app

# --- Punto de entrada para la ejecución ---
if __name__ == '__main__':
    app = create_app()
    
    # Leemos DEBUG_MODE de las variables de entorno de Render. Localmente será False.
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() == "true"
    
    # Render inyecta el puerto en la variable PORT. Si no existe (tu entorno local), usa 5000.
    port = int(os.environ.get("PORT", 5000))
    
    logging.info(f"Iniciando servidor Flask en puerto {port}")
    
    # HOST 0.0.0.0 es OBLIGATORIO en la nube
    app.run(host='0.0.0.0', port=port, debug=DEBUG_MODE)