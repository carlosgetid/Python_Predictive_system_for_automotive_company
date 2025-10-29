import streamlit as st
import pandas as pd
import requests
import os
import logging # Importar logging para mejor seguimiento

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Carga de Datos (MVP)",
    page_icon="📄",
    layout="wide"
)

# --- Tarea HU-001.T1: Diseño de la interfaz (Revertido a MVP) ---
st.title("HU-001: Carga de Datos Históricos (Transaccionales)")
st.markdown("""
Cargue aquí los archivos Excel de **Factura de Importación** (ej. `Factura_Importacion_PLUS_2024.xlsx`)
o un archivo CSV pre-procesado.

El sistema leerá automáticamente la hoja **'Detalle'** del Excel y extraerá
las columnas **'SKU'**, **'Fecha Venta'** y **'Cantidad'**.

Si carga un CSV, asegúrese de que contenga las columnas: `id_producto`, `fecha`, `cantidad_vendida`.
""")

# URL del backend (API Flask)
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BACKEND_URL_UPLOAD = f"http://{BACKEND_HOST}:{BACKEND_PORT}/upload" # Endpoint de carga

# --- Tarea HU-001.T2: Componente de Carga de Archivos ---
uploaded_file = st.file_uploader(
    "Seleccione un archivo (.csv, .xls, .xlsx)", # Permitir ambos tipos
    type=["csv", "xls", "xlsx"],
    accept_multiple_files=False,
    # Texto de ayuda actualizado
    help="Cargue el archivo Excel 'Factura_Importacion...' o un CSV con 'id_producto', 'fecha', 'cantidad_vendida'."
)

if uploaded_file is not None:
    st.success(f"Archivo '{uploaded_file.name}' cargado. Mostrando vista previa de las primeras filas.")

    # Mostrar vista previa (adaptada para leer 'Detalle' si es Excel)
    try:
        df_preview = None
        # Necesitamos leer el archivo para la vista previa sin consumirlo
        # Clonamos el objeto de archivo cargado en memoria
        from io import BytesIO
        file_bytes = BytesIO(uploaded_file.getvalue())

        if uploaded_file.name.endswith('.csv'):
            df_preview = pd.read_csv(file_bytes)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            try:
                # Leer solo la hoja 'Detalle' para la vista previa
                df_preview = pd.read_excel(file_bytes, sheet_name='Detalle', engine='openpyxl')
            except ValueError as sheet_error:
                 st.error(f"Error al leer la hoja 'Detalle' para la vista previa: {sheet_error}. Asegúrese que la hoja exista.")
                 # No continuar si no se puede leer la hoja principal
                 st.stop()
            except Exception as e:
                st.error(f"Error inesperado al leer el archivo Excel para vista previa: {e}")
                logging.error(f"Error previsualizando Excel: {e}", exc_info=True)
                st.stop()

        # Si la lectura fue exitosa, mostrar preview
        if df_preview is not None:
            st.subheader("Vista Previa (Hoja 'Detalle' o CSV)")
            st.dataframe(df_preview.head())

            # --- Botón de procesamiento ---
            st.markdown("---")
            if st.button("Procesar y Guardar en Base de Datos"):
                with st.spinner("Conectando con el backend... Validando y guardando datos..."):
                    # Preparamos el archivo REAL (no el clonado) para enviarlo a la API
                    uploaded_file.seek(0) # Asegurar que el puntero esté al inicio
                    files = {
                        'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }

                    try:
                        # Llamar al backend actualizado
                        response = requests.post(BACKEND_URL_UPLOAD, files=files, timeout=300) # Timeout más largo

                        if response.status_code == 201: # Creado
                            st.success("¡Éxito! Datos procesados y guardados.")
                            # Mostrar el resumen devuelto por el backend
                            st.json(response.json().get('data_summary', {}))
                        else:
                            # Mostrar error específico del backend
                            error_msg = response.json().get('error', f'Error {response.status_code} - {response.text}')
                            st.error(f"Error desde el backend: {error_msg}")

                    except requests.exceptions.ConnectionError:
                        st.error(f"Error de Conexión: No se pudo conectar al backend en {BACKEND_URL_UPLOAD}. ¿Está corriendo?")
                    except requests.exceptions.Timeout:
                        st.error("Error: La solicitud al backend tardó demasiado (timeout).")
                    except Exception as e:
                        st.error(f"Ocurrió un error inesperado al contactar el backend: {e}")
                        logging.error(f"Error al enviar archivo al backend: {e}", exc_info=True)
        else:
             st.warning("No se pudo generar la vista previa del archivo.")


    except Exception as e:
        st.error(f"Error al intentar leer o previsualizar el archivo: {e}")
        logging.error(f"Error en la previsualización: {e}", exc_info=True)
else:
    st.info("Por favor, cargue un archivo para continuar.")

