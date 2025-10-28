import pandas as pd
from flask import Blueprint, request, jsonify

# Importamos nuestra función de guardado
from backend.database.db_utils import save_dataframe_to_db

# Creamos un "Blueprint" de Flask. Esto nos permite organizar nuestras rutas
# de forma modular, en lugar de tener todo en un solo archivo.
api_bp = Blueprint('api', __name__)

# Definimos las columnas que esperamos en el archivo
REQUIRED_COLUMNS = {'id_producto', 'fecha', 'cantidad_vendida'}

def validate_dataframe(df):
    """
    Tarea HU-001.T4: Desarrollar la lógica de validación del formato y las columnas.
    Valida que el DataFrame tenga las columnas necesarias.
    """
    columnas_en_df = set(df.columns)
    
    if not REQUIRED_COLUMNS.issubset(columnas_en_df):
        columnas_faltantes = REQUIRED_COLUMNS - columnas_en_df
        return False, f"Validación fallida. Faltan las columnas: {columnas_faltantes}"
    
    # Asegurarnos de que 'fecha' sea tipo datetime
    try:
        df['fecha'] = pd.to_datetime(df['fecha'])
    except Exception as e:
        return False, f"Error al convertir la columna 'fecha'. Verifique el formato. Error: {e}"
        
    # Podemos añadir más validaciones aquí (ej. que cantidad_vendida sea numérico)
    
    return True, "Validación exitosa."


# Tarea HU-001.T3: Implementar el endpoint de la API REST para recibir el archivo
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint para recibir un archivo (CSV o Excel) y guardarlo en la BD
    después de validarlo.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo en la solicitud"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400
    
    try:
        # Leer el archivo directamente en un DataFrame de pandas
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return jsonify({"error": "Formato de archivo no soportado. Usar .csv o .xlsx"}), 400
        
        # Tarea HU-001.T4: Ejecutar la validación
        es_valido, mensaje = validate_dataframe(df)
        if not es_valido:
            return jsonify({"error": mensaje}), 400
            
        # Tarea HU-001.T5: Guardar en la base de datos
        # Seleccionamos solo las columnas que necesitamos antes de guardar
        df_to_save = df[list(REQUIRED_COLUMNS)]
        
        summary = save_dataframe_to_db(df_to_save, 'ventas_historicas')
        
        # Si todo sale bien, devolvemos un código 201 (Creado)
        return jsonify({
            "message": f"Archivo '{file.filename}' procesado y guardado con éxito.",
            "data_summary": summary
        }), 201

    except Exception as e:
        # Capturamos cualquier otro error (ej. error de BD, archivo corrupto)
        return jsonify({"error": f"Ocurrió un error interno: {e}"}), 500

