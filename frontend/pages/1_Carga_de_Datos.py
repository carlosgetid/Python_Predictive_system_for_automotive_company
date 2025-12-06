import streamlit as st
import pandas as pd
import requests
import os
import logging 
import sys
from pathlib import Path
from io import BytesIO

from frontend.config import get_setting # Para leer el archivo en memoria para la vista previa
# [NUEVO] Motor de estilos
from frontend.styles import get_app_css


# --- PROTECCIÓN DE PÁGINA (Login Required + RBAC) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

# Validación de Rol: Bloquear acceso a "Vendedora" (Ana)
if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos para cargar datos.")
    st.stop()
# ----------------------------------------------------

# --- LEER CONFIGURACIÓN DINÁMICA ---
# Leemos el estado actual desde el JSON cada vez que se carga la página
MOSTRAR_CARGA_MANUAL = get_setting("MOSTRAR_CARGA_MANUAL", True)

# Aquí solo establecemos el título de esta página específica.
# 1. Inyectar CSS Global
st.markdown(get_app_css(), unsafe_allow_html=True)

# 2. Encabezado Corporativo
st.markdown('<h1 style="color:#0F2942; margin-bottom: 10px;">📄 Ingesta de Datos Transaccionales</h1>', unsafe_allow_html=True)

# --- INICIO DEL BLOQUE CONDICIONAL ---
if MOSTRAR_CARGA_MANUAL:
    # --- Tarjeta de Instrucciones (Estilo Enterprise) ---
    st.markdown("""
    <div class="metric-card" style="padding: 20px; margin-bottom: 25px; border-left: 4px solid #0F2942;">
        <h4 style="margin-top:0; color:#334155; font-size: 16px;">Guía de Proceso</h4>
        <ol style="color:#64748B; margin-bottom:0; font-size: 14px; padding-left: 20px;">
            <li>Cargue el archivo <b>Excel</b> corporativo (<i>Factura_Importacion_PLUS_*.xlsx</i>).</li>
            <li>El sistema validará automáticamente la hoja <b>'Detalle'</b> y generará una vista previa.</li>
            <li>Confirme la consistencia de los datos y ejecute la carga a la base de datos.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    # URL del backend (API Flask)
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    BACKEND_URL_UPLOAD = f"http://{BACKEND_HOST}:{BACKEND_PORT}/upload" # Endpoint de carga

    # Configurar logging básico (opcional)
    logging.basicConfig(level=logging.INFO)

    # --- Contenedor Principal (Panel de Pasos) ---
    with st.container(border=True):
        # Paso 1 con estilo HTML
        st.markdown('<h3 style="color:#0F2942; font-size: 18px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">1. Selección de Archivo Fuente</h3>', unsafe_allow_html=True)
        
        # --- Tarea HU-001.T2: Componente de Carga de Archivos ---
        uploaded_file = st.file_uploader(
            "Cargar archivo Excel (.xls, .xlsx) o CSV (.csv)", # Etiqueta refinada
            type=["csv", "xls", "xlsx"],
            accept_multiple_files=False,
            help="Cargue el archivo Excel 'Factura_Importacion...' (leerá hoja 'Detalle') o un CSV con 'id_producto', 'fecha', 'cantidad_vendida'."
        )

        if uploaded_file is not None:
            # --- Vista Previa ---
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<h3 style="color:#0F2942; font-size: 18px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">2. Validación y Previsualización</h3>', unsafe_allow_html=True)
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
                        columnas_problematicas = ['HS Code', 'Margen Neto (PEN)']
                        
                        for col in columnas_problematicas:
                            if col in df_preview.columns:
                                df_preview[col] = df_preview[col].astype(str)
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

                        # --- Botón de procesamiento ---
                        st.markdown('<br>', unsafe_allow_html=True)
                        st.markdown('<h3 style="color:#0F2942; font-size: 18px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">3. Ejecución de Carga</h3>', unsafe_allow_html=True)
                        st.caption("Esta acción registrará los datos validados en el histórico permanente.")
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

else:
    # --- Vista cuando la funcionalidad está deshabilitada (Tarjeta de Estado) ---
    st.markdown("""
    <div class="metric-card" style="background-color: #F8FAFC; border-left: 5px solid #64748B;">
        <h3 style="color: #0F2942; margin-top: 0;">🔒 Modo Manual Deshabilitado</h3>
        <p style="color: #475569; font-size: 14px;">
            El sistema está operando bajo políticas de <b>Ingesta Automatizada (Batch)</b>.
            La carga manual a través de la interfaz web ha sido restringida por el administrador.
        </p>
        <div style="background-color: #E2E8F0; padding: 12px; border-radius: 6px; font-family: monospace; color: #334155; font-size: 13px; margin: 15px 0;">
            📥 Directorio de Entrada: /data_fuente/entrada/
        </div>
        <p style="color: #94A3B8; font-size: 12px; margin-bottom: 0;">
            Los archivos .xlsx depositados en el servidor serán procesados automáticamente por el worker de ingesta.
        </p>
    </div>
    """, unsafe_allow_html=True)