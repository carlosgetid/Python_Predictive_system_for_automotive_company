from flask import Flask, jsonify
from flask_cors import CORS

# Importamos nuestro blueprint de rutas
from backend.api.routes import api_bp
from backend.database.db_utils import test_db_connection

# Inicializamos la aplicación Flask
app = Flask(__name__)

# --- Configuración de CORS ---
# Habilitamos CORS (Cross-Origin Resource Sharing) para permitir
# que nuestro frontend (en localhost:8501) pueda hablar
# con nuestro backend (en localhost:5000).
CORS(app)

# --- Registro de Blueprints (Rutas) ---
# Le decimos a la app que use las rutas definidas en api_bp
# con el prefijo /api.
# Por lo tanto, nuestro endpoint de carga será: /api/upload
# ¡¡ACTUALIZACIÓN IMPORTANTE!!: Modifiqué el frontend para apuntar a /api/upload
# Voy a actualizar el frontend para que apunte a /api/upload
app.register_blueprint(api_bp, url_prefix='/')

# --- Ruta de Verificación (Health Check) ---
@app.route('/')
def health_check():
    """Ruta simple para verificar que el servidor está vivo."""
    return jsonify({"status": "Backend_is_running"})

@app.route('/test_db')
def test_db():
    """Ruta para verificar la conexión a la base de datos."""
    success, message = test_db_connection()
    if success:
        return jsonify({"status": "OK", "message": message})
    else:
        return jsonify({"status": "ERROR", "message": message}), 500


# --- Punto de entrada para ejecutar la app ---
if __name__ == '__main__':
    # Ejecutamos la app en modo debug (se reinicia con cambios)
    # y en el puerto 5000.
    app.run(debug=True, port=5000)

