import streamlit as st
import requests
import pandas as pd
import datetime
import logging
import os # Necesario para leer la URL del backend

# --- Configuración de la Página ---
st.set_page_config(layout="wide")
st.title("HU-003: Visualización de Predicción de Demanda (MVP)")
st.markdown("Consulta el modelo de ML para predecir la **cantidad de unidades** futuras.")

# --- Constantes de la API (Revertidas a MVP) ---
# Usar variable de entorno si existe, sino el valor por defecto
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BACKEND_URL_PREDICT = f"http://{BACKEND_HOST}:{BACKEND_PORT}/predict"
BACKEND_URL_HISTORY = f"http://{BACKEND_HOST}:{BACKEND_PORT}/history"

# Configurar logging (opcional, útil para debug)
logging.basicConfig(level=logging.INFO)

# --- Tarea HU-003.T1: Interfaz de Usuario (Entradas MVP) ---
st.subheader("Generar Nueva Predicción")
st.markdown("Seleccione un producto y una fecha futura para estimar la demanda en unidades.")

# Usamos un formulario para agrupar las entradas
with st.form(key="prediction_form_mvp"):

    # Campo para el ID del Producto (Revertido)
    id_producto = st.text_input(
        label="ID del Producto (SKU)",
        placeholder="Ej. FIL-A-001" # Usar un ejemplo válido de tus datos
    )

    # Campo para la Fecha (Revertido)
    fecha_seleccionada = st.date_input(
        label="Seleccione la fecha a predecir",
        value=datetime.date.today() + datetime.timedelta(days=7), # Por defecto, una semana adelante
        min_value=datetime.date.today() # No permitir predecir el pasado inmediato
    )

    # Botón de envío del formulario
    submit_button = st.form_submit_button(label="Generar Predicción de Unidades")

# --- Lógica de la Aplicación (Al presionar el botón) ---
if submit_button:
    if not id_producto:
        st.warning("Por favor, ingrese un ID de Producto (SKU).")
    else:
        # Convertir fecha a string YYYY-MM-DD
        fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")

        # Payload para /predict (MVP)
        payload_predict = {
            "id_producto": id_producto,
            "fecha_str": fecha_str
        }

        # Payload para /history (MVP)
        payload_history = {
            "id_producto": id_producto
        }

        st.markdown("---")
        with st.spinner(f"Consultando modelo e historial para '{id_producto}'..."):
            try:
                # --- Llamadas a los Endpoints del Backend ---
                response_pred = requests.post(BACKEND_URL_PREDICT, json=payload_predict, timeout=60)
                response_hist = requests.post(BACKEND_URL_HISTORY, json=payload_history, timeout=60)

                # Dividir pantalla
                col1, col2 = st.columns([1, 2])

                # --- Mostrar Resultado Predicción (Col 1) ---
                with col1:
                    st.subheader("Predicción")
                    if response_pred.status_code == 200:
                        data_pred = response_pred.json()
                        prediccion_unidades = data_pred.get("prediccion") # El backend devuelve 'prediccion'

                        if prediccion_unidades is not None:
                            st.metric(
                                label=f"Demanda Predicha para '{id_producto}'",
                                value=f"{prediccion_unidades} unidades", # Mostrar en unidades
                                help=f"Predicción de unidades para el día {fecha_str}."
                            )
                        else:
                            st.error("El backend devolvió una respuesta inesperada (predicción nula).")

                    elif response_pred.status_code == 404:
                         # El backend devuelve 404 si el producto es desconocido
                         st.error(f"Error 404: {response_pred.json().get('error', 'Producto no encontrado o desconocido para el modelo')}")
                    else:
                        st.error(f"Error del Backend (Predicción): {response_pred.status_code} - {response_pred.text}")

                # --- Mostrar Historial (Col 2) ---
                with col2:
                    st.subheader("Historial de Ventas (Unidades)")
                    if response_hist.status_code == 200:
                        data_hist = response_hist.json().get("historial", [])

                        if data_hist:
                            try:
                                df_hist = pd.DataFrame(data_hist)
                                # Convertir 'fecha' a datetime (el backend ya la devuelve como string ISO)
                                df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
                                # Asegurar que cantidad_vendida es numérica
                                df_hist['cantidad_vendida'] = pd.to_numeric(df_hist['cantidad_vendida'])
                                # Usar fecha como índice y ordenar para el gráfico
                                df_hist = df_hist.set_index('fecha').sort_index()

                                # Graficar cantidad_vendida
                                st.line_chart(df_hist['cantidad_vendida'])
                            except Exception as e:
                                st.error(f"Error al procesar o graficar el historial: {e}")
                                logging.error(f"Error procesando historial: {e}", exc_info=True)

                        else:
                            st.info(f"No se encontró historial de ventas para '{id_producto}'.")
                    else:
                        st.error(f"Error del Backend (Historial): {response_hist.status_code} - {response_hist.text}")

            except requests.exceptions.ConnectionError:
                st.error(f"Error de Conexión: No se pudo conectar al backend en {BACKEND_URL_PREDICT}. ¿Está corriendo?")
            except requests.exceptions.Timeout:
                 st.error("Error: La solicitud al backend tardó demasiado (timeout).")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado en el frontend: {e}")
                logging.error(f"Error inesperado en frontend: {e}", exc_info=True)
