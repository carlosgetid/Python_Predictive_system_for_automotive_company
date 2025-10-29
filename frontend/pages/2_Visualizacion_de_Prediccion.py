import streamlit as st
import requests
import pandas as pd
import datetime
import logging

# --- Configuración de la Página ---
st.set_page_config(layout="wide")
st.title("HU-003: Visualización de Predicción de Stock")
st.markdown("Esta página consulta el modelo de ML para predecir la demanda futura.")

# --- Constantes de la API ---
# (Asegúrate de que tu backend esté corriendo en el puerto 5000)
BACKEND_URL_PREDICT = "http://127.0.0.1:5000/predict"
BACKEND_URL_HISTORY = "http://127.0.0.1:5000/history"

# --- Tarea HU-003.T1: Interfaz de Usuario (Entradas) ---
st.subheader("Generar Nueva Predicción")
st.markdown("Seleccione un producto y una fecha futura para estimar la demanda.")

# Usamos un formulario para agrupar las entradas
with st.form(key="prediction_form"):
    
    # Campo para el ID del Producto
    id_producto = st.text_input(
        label="ID del Producto (SKU)",
        placeholder="Ej. FIL-A-001"
    )
    
    # Campo para la Fecha
    fecha_seleccionada = st.date_input(
        label="Seleccione la fecha a predecir",
        value=datetime.date.today() + datetime.timedelta(days=1), # Por defecto, mañana
        min_value=datetime.date.today() # No permitir predecir el pasado
    )
    
    # Botón de envío del formulario
    submit_button = st.form_submit_button(label="Generar Predicción")

# --- Lógica de la Aplicación (Al presionar el botón) ---
if submit_button:
    if not id_producto:
        st.warning("Por favor, ingrese un ID de Producto.")
    else:
        # Convertimos la fecha a string en el formato esperado por el backend (YYYY-MM-DD)
        fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
        
        # Payload para el endpoint /predict
        payload_predict = {
            "id_producto": id_producto,
            "fecha_str": fecha_str
        }
        
        # Payload para el endpoint /history
        payload_history = {
            "id_producto": id_producto
        }
        
        # Iniciar la consulta a los dos endpoints
        st.markdown("---")
        with st.spinner(f"Consultando al modelo y buscando historial para '{id_producto}'..."):
            try:
                # --- Tarea HU-003.T2: Componente Visual (Métrica) ---
                
                # 1. Llamada al endpoint de PREDICCIÓN
                response_pred = requests.post(BACKEND_URL_PREDICT, json=payload_predict)
                
                # 2. Llamada al endpoint de HISTORIAL
                response_hist = requests.post(BACKEND_URL_HISTORY, json=payload_history)

                # Dividimos la pantalla en 2 columnas para los resultados
                col1, col2 = st.columns([1, 2])

                # --- Mostrar Resultado de la Predicción (Columna 1) ---
                with col1:
                    st.subheader("Predicción")
                    if response_pred.status_code == 200:
                        data_pred = response_pred.json()
                        prediccion = data_pred.get("prediccion")
                        
                        if prediccion is not None:
                            st.metric(
                                label=f"Demanda Predicha para '{id_producto}'",
                                value=f"{prediccion} unidades",
                                help=f"Predicción para el día {fecha_str}."
                            )
                        else:
                            # Esto puede pasar si el 'id_producto' era desconocido (404)
                            st.error(f"Error: {data_pred.get('error', 'Error desconocido')}")

                    elif response_pred.status_code == 404:
                         st.error(f"Error: {response_pred.json().get('error', 'Producto no encontrado')}")
                    else:
                        st.error(f"Error del Backend (Predicción): {response_pred.status_code}")

                # --- Tarea HU-003.T2: Componente Visual (Gráfico) ---
                
                # --- Mostrar Resultado del Historial (Columna 2) ---
                with col2:
                    st.subheader("Historial de Ventas")
                    if response_hist.status_code == 200:
                        data_hist = response_hist.json().get("historial", [])
                        
                        if data_hist:
                            df_hist = pd.DataFrame(data_hist)
                            # Convertir la columna de fecha a datetime
                            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
                            # Usar la fecha como índice para el gráfico
                            df_hist = df_hist.set_index('fecha')
                            
                            st.line_chart(df_hist['cantidad_vendida'])
                        else:
                            st.info("No se encontró historial de ventas para este producto.")
                    else:
                        st.error(f"Error del Backend (Historial): {response_hist.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("Error de Conexión: No se pudo conectar al servidor Backend. "
                         "¿Está el backend (python -m backend.app) corriendo?")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
                logging.error(f"Error en frontend: {e}")

