import logging
from flask import Flask
from flask_cors import CORS
from backend.config import DEBUG_MODE
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
    # Todas las rutas definidas en routes.py ahora estarán bajo '/'
    app.register_blueprint(api_bp, url_prefix='/')

    @app.route('/health')
    def health_check():
        """
        Un endpoint simple para verificar que el servidor está vivo.
        """
        logging.info("Health check endpoint fue llamado.")
        return {"status": "ok"}, 200
    
    return app

# --- Punto de entrada para la ejecución ---
if __name__ == '__main__':
    app = create_app()
    logging.info("Iniciando servidor Flask en http://127.0.0.1:5000")
    # Usamos host y port definidos para asegurarnos
    app.run(host='127.0.0.1', port=5000, debug=DEBUG_MODE)

