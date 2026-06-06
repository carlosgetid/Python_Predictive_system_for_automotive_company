import streamlit as st
import requests
import pandas as pd
import datetime
import logging
import os 
import sys
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    from frontend.config import URL_PREDICT, BASE_URL, get_role_based_sidebar_css
    # [NUEVO] Importar motor de estilos
    from frontend.styles import get_app_css 
    # Construimos URL_HISTORY usando la base importada
    URL_HISTORY = f"{BASE_URL}/history"
except ImportError:
    # Fallback
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    URL_PREDICT = f"{BASE_URL}/predict"
    URL_HISTORY = f"{BASE_URL}/history"

URL_ALERTS = f"{BASE_URL}/api/alerts"
URL_ALERTS_STATUS = f"{BASE_URL}/api/alerts/{{}}/status"

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

# --- PROTECCIÓN DE PÁGINA (Login Required) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.switch_page("pages/login.py")

# --- RBAC VISUAL: Ocultar pestañas no permitidas ---
# Esto asegura que Ana no vea enlaces a Admin/Carga mientras está aquí
role_css = get_role_based_sidebar_css(st.session_state.user['rol'])
st.markdown(role_css, unsafe_allow_html=True)
# ---------------------------------------------------

# ---------------------------------------------------

# [NUEVO] Inyectar CSS Global para el estilo Enterprise
st.markdown(get_app_css(), unsafe_allow_html=True)

# [NUEVO] Título Corporativo
st.markdown('<h1 style="color:#0F2942; margin-bottom: 5px;">📈 Visualización y Pronóstico de Demanda</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748B;">Utilice este panel para generar un pronóstico de demanda de unidades para cualquier SKU en una fecha futura.</p>', unsafe_allow_html=True)

# --- INICIO DE AGREGADO: Alertas Activas (HU-007) ---
def fetch_alerts():
    try:
        response = requests.get(URL_ALERTS, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logging.error(f"Error fetching alerts: {e}")
        return []

def update_alert_status(alert_id, new_status):
    try:
        url = URL_ALERTS_STATUS.format(alert_id)
        response = requests.put(url, json={"estado": new_status}, timeout=10)
        if response.status_code == 200:
            st.success(f"Alerta {new_status.lower()} exitosamente.")
            return True
        st.error(f"Error al actualizar alerta: {response.text}")
        return False
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False

@st.dialog("Confirmación Requerida")
def confirm_discard_dialog(alert_id, original_display):
    st.warning("¿Estás seguro que quieres descartar esta alerta? Desaparecerá de tu lista de pendientes.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sí, descartar", type="primary", use_container_width=True):
            if update_alert_status(alert_id, "DESCARTADA"):
                st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.session_state[f"status_{alert_id}"] = original_display
            st.rerun()

with st.expander("🔔 Alertas Activas de Inventario", expanded=True):
    alertas = fetch_alerts()
    if not alertas:
        st.info("✅ No hay alertas pendientes. Todo en orden.")
    else:
        st.warning(f"Se han detectado {len(alertas)} alertas pendientes que requieren su atención.")
        # Utilizar columnas para mostrar las alertas de forma clara
        for alert in alertas:
            col1, col2, col3, col4 = st.columns([1.5, 1, 3, 1.5])
            with col1:
                st.markdown(f"**SKU:** {alert['sku']}")
            with col2:
                # Color code type
                color = "red" if alert['tipo_alerta'] == 'QUIEBRE' else "orange"
                st.markdown(f"<span style='color:{color}; font-weight:bold;'>{alert['tipo_alerta']}</span>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<small>{alert['mensaje']}</small>", unsafe_allow_html=True)
            with col4:
                # Botones de acción reemplazados por Selectbox con indicadores visuales
                status_map = {
                    "PENDIENTE": "🔴 PENDIENTE",
                    "EN GESTIÓN": "🟡 EN GESTIÓN",
                    "DESCARTADA": "⚪ DESCARTADA"
                }
                inverse_map = {v: k for k, v in status_map.items()}
                
                current_status = alert.get('estado', 'PENDIENTE')
                current_display = status_map.get(current_status, "🔴 PENDIENTE")
                opciones_display = list(status_map.values())
                
                try:
                    idx = opciones_display.index(current_display)
                except ValueError:
                    idx = 0
                
                new_display = st.selectbox(
                    "Estado",
                    options=opciones_display,
                    index=idx,
                    key=f"status_{alert['id']}",
                    label_visibility="collapsed"
                )
                
                new_status = inverse_map[new_display]
                
                if new_status != current_status:
                    if new_status == "DESCARTADA":
                        confirm_discard_dialog(alert['id'], current_display)
                    else:
                        if update_alert_status(alert['id'], new_status):
                            st.rerun()
            st.markdown("---")
# --- FIN DE AGREGADO ---

# --- Tarea HU-003.T1: Diseño de la interfaz (Rediseñado - Fase 4) ---
st.markdown("""
<div class="metric-card" style="padding: 15px; margin-bottom: 25px; border-left: 4px solid #0F2942;">
    <h4 style="margin-top:0; color:#334155; font-size: 16px;">Instrucciones Rápidas</h4>
    <p style="color:#64748B; margin-bottom:0; font-size: 14px;">
        1. Ingrese el ID del Producto (SKU) a consultar.<br>
        2. Seleccione la fecha futura para la cual desea el pronóstico.<br>
        3. El sistema usará el modelo Híbrido (MLP + XGBoost) para la predicción.
    </p>
</div>
""", unsafe_allow_html=True)

# --- Contenedor de Entradas (Fase 4 - Tarea 2) ---
st.markdown('<h3 style="color:#0F2942; font-size: 18px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">Generar Nueva Predicción</h3>', unsafe_allow_html=True)

# Usamos un formulario para agrupar las entradas
with st.form(key="prediction_form_mvp_redesign"):
# ... (dejar el resto del formulario sin cambios hasta el final de la sección)

        # Campo para el ID del Producto
        id_producto = st.text_input(
            label="ID del Producto (SKU)"
        )

        # Campo para la Fecha
        fecha_seleccionada = st.date_input(
            label="Seleccione la fecha a predecir",
            value=datetime.date.today() + datetime.timedelta(days=7), # Por defecto, una semana adelante
            min_value=datetime.date.today() + datetime.timedelta(days=1) # Mínimo mañana
        )

        # Botón de envío del formulario
        submit_button = st.form_submit_button(
            label="Generar Predicción de Unidades",
            type="primary" # Usar el color primario del tema
        )

st.markdown('</div>', unsafe_allow_html=True) # [NUEVO] Cierre del div de la tarjeta    

# --- Lógica de la Aplicación (Al presionar el botón) ---
if submit_button:
    if not id_producto:
        st.warning("Por favor, ingrese un ID de Producto (SKU).")
    else:
        # Convertir fecha a string YYYY-MM-DD
        fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")

        # Payloads para el backend
        payload_predict = {"id_producto": id_producto, "fecha_str": fecha_str}
        payload_history = {"id_producto": id_producto}

        # --- Contenedor de Resultados (Fase 4 - Tarea 3) ---
        st.markdown(f'<h3 style="color:#0F2942; font-size: 18px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">Resultados para: {id_producto}</h3>', unsafe_allow_html=True)
            
        with st.spinner(f"Consultando modelo e historial..."):
            try:
# ... (rest of the logic)
                # --- Llamadas a los Endpoints del Backend ---
                # Inyectar token JWT en cabeceras para acceso seguro (HU-008)
                headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
                
                response_pred = requests.post(URL_PREDICT, json=payload_predict, headers=headers, timeout=60)
                response_hist = requests.post(URL_HISTORY, json=payload_history, headers=headers, timeout=60)

                # --- Manejo de Errores de Autenticación/Autorización ---
                if response_pred.status_code == 401:
                    st.error("🔒 Su sesión ha expirado o el token es inválido. Por favor, inicie sesión nuevamente.")
                    st.session_state.authenticated = False
                    st.session_state.user = None
                    st.session_state.token = None
                    st.session_state.rol = None
                    time.sleep(2)
                    st.rerun()
                elif response_pred.status_code == 403:
                    st.warning("⛔ Acceso denegado: Su rol no tiene permisos suficientes para generar predicciones.")
                else:
                    # Dividir pantalla
                    col1, col2 = st.columns([1, 2])

                    # --- Mostrar Resultado Predicción (Col 1) ---
                    with col1:
                        # [CORRECCIÓN] Reemplazo de st.subheader por título HTML
                        st.markdown('<h4 style="color: #64748B; font-size: 16px; margin-bottom: 0;">Pronóstico IA</h4>', unsafe_allow_html=True)
                        if response_pred.status_code == 200:
                            data_pred = response_pred.json()
                            prediccion_unidades = data_pred.get("prediccion")

                            if prediccion_unidades is not None:
                                # [CORRECCIÓN] Reemplazo de st.metric por HTML/CSS de alto impacto
                                st.markdown(f"""
                                <div style="margin-top: 10px; padding: 15px; background-color: #F8FAFC; border-radius: 8px; border: 1px solid #10B981;">
                                    <p style="font-size: 0.8rem; color: #64748B; margin-bottom: 5px;">Demanda para el {fecha_str}</p>
                                    <span class="metric-value" style="color: var(--success); font-size: 2.5rem;">
                                        {prediccion_unidades}
                                    </span>
                                    <span style="font-size: 1.2rem; color: #334155;">unidades</span>
                                    <p style="font-size: 0.7rem; color: #94A3B8; margin-top: 5px; margin-bottom: 0;">Generado por modelo Híbrido.</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("El backend devolvió una respuesta inesperada (predicción nula).")

                        elif response_pred.status_code == 404:
                                error_msg = response_pred.json().get('error', 'Producto no encontrado o desconocido para el modelo')
                                st.error(f"Error 404: {error_msg}")
                        else:
                            st.error(f"Error del Backend (Predicción): {response_pred.status_code} - {response_pred.text}")

                    # --- Mostrar Historial (Col 2) ---
                    with col2:
                        # [CORRECCIÓN] Reemplazo de st.subheader por título HTML
                        st.markdown('<h4 style="color: #64748B; font-size: 16px; margin-bottom: 0;">Histórico de Ventas</h4>', unsafe_allow_html=True)
                        if response_hist.status_code == 200:
                            data_hist = response_hist.json().get("historial", [])

                            if data_hist:
                                try:
                                    df_hist = pd.DataFrame(data_hist)
                                    df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
                                    df_hist['cantidad_vendida'] = pd.to_numeric(df_hist['cantidad_vendida'])
                                    df_hist = df_hist.set_index('fecha').sort_index()
                                    
                                    st.line_chart(df_hist['cantidad_vendida'], use_container_width=True)
                                
                                except Exception as e:
                                    st.error(f"Error al procesar o graficar el historial: {e}")
                                    logging.error(f"Error procesando historial: {e}", exc_info=True)

                            else:
                                st.info(f"No se encontró historial de ventas para este SKU.")
                        else:
                            st.error(f"Error del Backend (Historial): {response_hist.status_code} - {response_hist.text}")

                    # --- HU-004: Exportación de Reportes ---
                    st.markdown("---")
                    with st.expander("📥 Exportar Resultados", expanded=True):
                        st.markdown("Seleccione el formato para descargar el reporte predictivo.")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
                        # Preparar datos para exportación
                        import io
                        from frontend.utils.export_utils import generate_excel_report, generate_pdf_report
                        
                        hist_data = response_hist.json().get("historial", []) if response_hist.status_code == 200 else []
                        
                        df_export = pd.DataFrame(hist_data) if hist_data else pd.DataFrame(columns=['fecha', 'cantidad_vendida'])
                        if not df_export.empty:
                            df_export['fecha'] = pd.to_datetime(df_export['fecha']).dt.strftime('%Y-%m-%d')
                            df_export['Tipo'] = 'Histórico'
                        
                        if response_pred.status_code == 200 and data_pred.get("prediccion") is not None:
                            df_export = pd.concat([df_export, pd.DataFrame([{
                                'fecha': fecha_str, 
                                'cantidad_vendida': prediccion_unidades, 
                                'Tipo': 'Predicción'
                            }])], ignore_index=True)
                        
                        # Renombrar columnas para el reporte
                        df_export = df_export.rename(columns={'fecha': 'Fecha', 'cantidad_vendida': 'Unidades', 'Tipo': 'Tipo de Dato'})
                        
                        kpis = {
                            "SKU Analizado": id_producto,
                            "Fecha de Predicción": fecha_str,
                            "Unidades Predichas": prediccion_unidades if response_pred.status_code == 200 else "N/A"
                        }
                        if hist_data:
                            historico_vals = [float(x['cantidad_vendida']) for x in hist_data]
                            kpis["Promedio Histórico"] = round(sum(historico_vals) / len(historico_vals), 2)
                            kpis["Total Histórico"] = sum(historico_vals)
                            
                        user_name = st.session_state.user.get('nombre', 'Usuario')
                        fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        with col_btn1:
                            with st.spinner("Preparando PDF..."):
                                pdf_bytes = generate_pdf_report(df_export, kpis, user_name, "v1.0-XGBoost-MLP")
                            st.download_button(
                                label="📄 Descargar PDF",
                                data=pdf_bytes,
                                file_name=f"reporte_prediccion_{id_producto}_{fecha_actual}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                                
                        with col_btn2:
                            with st.spinner("Preparando Excel..."):
                                excel_bytes = generate_excel_report(df_export, kpis, user_name, "v1.0-XGBoost-MLP")
                            st.download_button(
                                label="📊 Descargar Excel",
                                data=excel_bytes,
                                file_name=f"reporte_prediccion_{id_producto}_{fecha_actual}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

            except requests.exceptions.ConnectionError:
                st.error(f"Error de Conexión: No se pudo conectar al backend en {URL_PREDICT}.")
            except requests.exceptions.Timeout:
                    st.error("Error: La solicitud al backend tardó demasiado (timeout).")
            except Exception as e:
                st.error(f"Ocurrió un error inesperado en el frontend: {e}")
                logging.error(f"Error inesperado en frontend: {e}", exc_info=True)

        st.markdown('</div>', unsafe_allow_html=True) # [NUEVO] Cierre del div de la tarjeta de resultados

