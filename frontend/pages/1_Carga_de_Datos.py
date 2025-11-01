import streamlit as st
import pandas as pd
import requests
import os
import logging 
from io import BytesIO # Para leer el archivo en memoria para la vista previa

# --- Configuración de la Página ---
# st.set_page_config debe estar en la página principal (Home.py)
# Aquí solo establecemos el título de esta página específica.
st.title("📄 Carga de Datos Transaccionales")

# --- Tarea HU-001.T1: Diseño de la interfaz (Rediseñado) ---
st.markdown("""
Esta página le permite cargar nuevos datos históricos de ventas al sistema.

1.  Cargue un archivo Excel (ej. `Factura_Importacion_PLUS_*.xlsx`). El sistema leerá la hoja **'Detalle'**.
2.  Revise la vista previa para confirmar que los datos son correctos.
3.  Haga clic en "Procesar" para guardar los datos en la base de datos.
""")

# URL del backend (API Flask)
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BACKEND_URL_UPLOAD = f"http://{BACKEND_HOST}:{BACKEND_PORT}/upload" # Endpoint de carga

# Configurar logging básico (opcional)
logging.basicConfig(level=logging.INFO)

# --- Contenedor Principal (Fase 3 - Tarea 3) ---
# Agrupamos toda la funcionalidad en un contenedor visual
with st.container(border=True):

    st.subheader("Paso 1: Seleccionar Archivo")
    
    # --- Tarea HU-001.T2: Componente de Carga de Archivos ---
    uploaded_file = st.file_uploader(
        "Cargar archivo Excel (.xls, .xlsx) o CSV (.csv)", # Etiqueta refinada
        type=["csv", "xls", "xlsx"],
        accept_multiple_files=False,
        help="Cargue el archivo Excel 'Factura_Importacion...' (leerá hoja 'Detalle') o un CSV con 'id_producto', 'fecha', 'cantidad_vendida'."
    )

    if uploaded_file is not None:
        # --- Vista Previa (Fase 3 - Tarea 5) ---
        st.subheader("Paso 2: Revisar Vista Previa")
        try:
            df_preview = None
            # Clonamos el objeto de archivo cargado en memoria
            file_bytes = BytesIO(uploaded_file.getvalue())

            if uploaded_file.name.endswith('.csv'):
                df_preview = pd.read_csv(file_bytes)
                preview_source = "CSV"
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                try:
                    # Leer solo la hoja 'Detalle' para la vista previa
                    df_preview = pd.read_excel(file_bytes, sheet_name='Detalle', engine='openpyxl')
                    preview_source = "Excel (hoja 'Detalle')"
                except ValueError as sheet_error:
                     st.error(f"Error al leer la hoja 'Detalle' para la vista previa: {sheet_error}. Asegúrese que la hoja exista y el archivo no esté corrupto.")
                     st.stop() # No continuar si no se puede leer la hoja principal
                except Exception as e:
                    st.error(f"Error inesperado al leer el archivo Excel para vista previa: {e}")
                    logging.error(f"Error previsualizando Excel: {e}", exc_info=True)
                    st.stop()
            else:
                st.error("Tipo de archivo no reconocido para vista previa.")
                st.stop()

            # Si la lectura fue exitosa, mostrar preview
            if df_preview is not None:
                if not df_preview.empty:
                    st.dataframe(df_preview.head())

                    # --- Botón de procesamiento (Fase 3 - Tarea 3) ---
                    st.subheader("Paso 3: Guardar en Base de Datos")
                    if st.button("Procesar y Guardar en Base de Datos"): # El color lo toma del config.toml
                        with st.spinner("Conectando con el backend... Validando y guardando datos..."):
                            # Preparamos el archivo REAL para enviarlo a la API
                            uploaded_file.seek(0) 
                            files = {
                                'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                            }

                            try:
                                response = requests.post(BACKEND_URL_UPLOAD, files=files, timeout=300) 

                                # --- Feedback Visual (Fase 3 - Tarea 5) ---
                                if response.status_code == 201: # Creado
                                    st.success("¡Éxito! Datos procesados y guardados en la base de datos.")
                                    st.json(response.json().get('data_summary', {}))
                                else:
                                    try:
                                        error_json = response.json()
                                        error_msg = error_json.get('error', f'Error {response.status_code} - Respuesta no JSON')
                                    except requests.exceptions.JSONDecodeError:
                                        error_msg = f'Error {response.status_code} - {response.text[:200]}'
                                    st.error(f"Error desde el backend: {error_msg}")

                            except requests.exceptions.ConnectionError:
                                st.error(f"Error de Conexión: No se pudo conectar al backend en {BACKEND_URL_UPLOAD}.")
                            except requests.exceptions.Timeout:
                                st.error("Error: La solicitud al backend tardó demasiado (timeout).")
                            except Exception as e:
                                st.error(f"Ocurrió un error inesperado al contactar el backend: {e}")
                                logging.error(f"Error al enviar archivo al backend: {e}", exc_info=True)
                
                elif df_preview is not None and df_preview.empty:
                    st.warning("El archivo o la hoja 'Detalle' parece estar vacía.")
                
                else:
                     st.warning("No se pudo generar la vista previa del archivo.")

        except Exception as e:
            st.error(f"Error al intentar leer o previsualizar el archivo: {e}")
            logging.error(f"Error en la previsualización: {e}", exc_info=True)
    else:
        # Mensaje por defecto cuando no hay archivo
        st.info("Por favor, cargue un archivo para comenzar.")

