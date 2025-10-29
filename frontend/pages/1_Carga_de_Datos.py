import streamlit as st
import pandas as pd
import requests
import os

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Carga de Datos",
    page_icon="📄",
    layout="wide"
)

# --- Tarea HU-001.T1: Diseño de la interfaz ---
st.title("HU-001: Carga de Datos Históricos")
st.markdown("""
Esta es la primera etapa del flujo de trabajo. Por favor, seleccione un archivo
(Excel o CSV) que contenga los datos históricos de ventas. El sistema validará
el archivo y lo guardará en la base de datos.
""")

# URL del backend (API Flask)
# Usamos variables de entorno si están disponibles, sino un valor por defecto
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000/upload")

# --- Tarea HU-001.T2: Componente de Carga de Archivos ---
uploaded_file = st.file_uploader(
    "Seleccione un archivo (.csv o .xlsx)",
    type=["csv", "xlsx"],
    accept_multiple_files=False,
    help="Cargue un archivo CSV o Excel con las columnas: id_producto, fecha, cantidad_vendida"
)

if uploaded_file is not None:
    # Si el archivo se carga, mostrar un mensaje de éxito y una vista previa
    st.success(f"Archivo '{uploaded_file.name}' cargado. Mostrando vista previa.")
    
    # Leer el archivo en un dataframe de pandas para mostrar la vista previa
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            # Asumimos que es .xlsx
            df = pd.read_excel(uploaded_file)
        
        st.subheader("Vista Previa de los Datos (Primeras 5 filas)")
        st.dataframe(df.head())

        # --- Botón de procesamiento ---
        st.markdown("---")
        if st.button("Procesar y Guardar en Base de Datos"):
            
            # --- Conexión con Tareas de Backend (HU-001.T3, T4, T5) ---
            with st.spinner("Conectando con el backend... Validando y guardando datos..."):
                
                # Preparamos el archivo para enviarlo a la API
                # Necesitamos re-leer el archivo en modo binario para 'requests'
                uploaded_file.seek(0)
                files = {
                    'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                }
                
                try:
                    # Tarea HU-001.T3: Implementar el endpoint de la API REST
                    response = requests.post(BACKEND_URL, files=files, timeout=300)
                    
                    # Tarea HU-001.T4 y T5: Lógica de validación y guardado (en el backend)
                    if response.status_code == 201:
                        st.success(f"¡Éxito! {response.json().get('message')}")
                        st.json(response.json().get('data_summary'))
                    else:
                        # Mostrar error si el backend devuelve uno (ej. validación fallida)
                        st.error(f"Error desde el backend: {response.json().get('error', 'Error desconocido')}")
                
                except requests.exceptions.ConnectionError:
                    st.error(f"Error de Conexión: No se pudo conectar al backend en {BACKEND_URL}. ¿Está el servidor Flask corriendo?")
                except Exception as e:
                    st.error(f"Ocurrió un error inesperado: {e}")

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
else:
    st.info("Por favor, cargue un archivo para continuar.")