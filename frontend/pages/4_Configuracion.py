import streamlit as st
import sys
import logging
from pathlib import Path
import requests

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
# Necesario para importar frontend.config correctamente
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    from frontend.config import get_setting, update_setting, BASE_URL
    # [NUEVO] Importar motor de estilos
    from frontend.styles import get_app_css
except ImportError as e:
    # Si no se exporta BASE_URL, hacemos un fallback seguro
    try:
        from frontend.config import get_setting, update_setting
        from frontend.styles import get_app_css
        import os
        BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
        BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
        BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    except ImportError as e:
        st.error(f"Error crítico importando configuración: {e}")
        st.stop()

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

# --- PROTECCIÓN DE PÁGINA (Login Required + RBAC) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

# Validación de Rol: Bloquear acceso a "Vendedora"
if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos de configuración.")
    st.stop()
# ----------------------------------------------------

# ----------------------------------------------------

# [NUEVO] Inyectar CSS Global para el estilo Enterprise
st.markdown(get_app_css(), unsafe_allow_html=True)

# [REEMPLAZO] Encabezado Corporativo
st.markdown('<h1 style="color:#0F2942; margin-bottom: 5px;">⚙️ Configuración del Sistema</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748B;">Panel de control para ajustar el comportamiento de la interfaz y funcionalidades del sistema.</p>', unsafe_allow_html=True)

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) 

# --- SECCIÓN: CONTROL DE INGESTA ---
# [REEMPLAZO] Subtítulo estilizado con separador
st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📂 Control de Ingesta de Datos</h2>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    # [REEMPLAZO] Usar metric-card para encapsular las instrucciones
    st.markdown("""
    <div class="metric-card" style="padding: 20px; border-left: 4px solid #0F2942;">
        <h4 style="margin-top:0; color:#0F2942; font-size: 16px;">Habilitar Carga Manual de Archivos</h4>
        <p style="color:#475569; margin-bottom: 10px; font-size: 14px;">
        Define si los usuarios pueden subir archivos Excel/CSV manualmente desde la interfaz web.
        </p>
        <ul style="color:#64748B; font-size: 13px; margin-bottom: 0; padding-left: 20px;">
            <li><b>Activado (ON):</b> Muestra el cargador en 'Carga de Datos'.</li>
            <li><b>Desactivado (OFF):</b> Se utiliza exclusivamente la Ingesta Automatizada (carpeta <code>/data_fuente/entrada</code>).</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # 1. Leer estado actual
# ... (el resto del código en col2 permanece igual)
    # 1. Leer estado actual
    current_state = get_setting("MOSTRAR_CARGA_MANUAL", True)
    
    # 2. Widget de control (Toggle Switch)
    # key='toggle_manual' asegura que el estado se mantenga en la sesión
    new_state = st.toggle("Estado", value=current_state, key="toggle_manual")

    # 3. Lógica de Guardado
    if new_state != current_state:
        if update_setting("MOSTRAR_CARGA_MANUAL", new_state):
            st.toast(f"Configuración guardada: {'Habilitado' if new_state else 'Deshabilitado'}", icon="✅")
            logging.info(f"Configuración MOSTRAR_CARGA_MANUAL cambiada a {new_state}")
            
            # Pequeña pausa para que el usuario vea el cambio antes de cualquier recarga
            import time
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Error al guardar en settings.json")

# --- Indicador Visual del Estado Actual (REEMPLAZO) ---
if new_state:
    st.markdown("""
    <div style="margin-top: 15px; padding: 10px; background-color: #D1FAE5; color: #10B981; border-radius: 6px; font-weight: 600; border: 1px solid #10B981;">
        ✅ La carga manual está HABILITADA actualmente.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="margin-top: 15px; padding: 10px; background-color: #F0F4F8; color: #64748B; border-radius: 6px; border: 1px solid #94A3B8;">
        ℹ️ La carga manual está DESHABILITADA. El sistema opera en modo automático.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- INICIO DE AGREGADO: Configuración de Correo y Alertas (HU-007) ---
st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📧 Notificaciones y Alertas (SMTP)</h2>', unsafe_allow_html=True)

URL_CONFIG_API = f"{BASE_URL}/api/config"
URL_CONFIG_TEST = f"{BASE_URL}/api/config/test-email"

def fetch_email_config():
    try:
        response = requests.get(URL_CONFIG_API, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"Error al obtener configuración: {e}")
    return {}

current_config = fetch_email_config()

with st.form("email_config_form"):
    st.markdown("Configure los parámetros para el envío automático de alertas de inventario.")
    c1, c2 = st.columns(2)
    with c1:
        smtp_host = st.text_input("Host SMTP", value=current_config.get("smtp_host", "smtp.gmail.com"))
        smtp_port = st.number_input("Puerto SMTP", value=int(current_config.get("smtp_port", 587)), step=1)
        email_remitente = st.text_input("Email Remitente (From)", value=current_config.get("email_remitente", "alertas@predictivo.auto"))
    with c2:
        smtp_user = st.text_input("Usuario SMTP (Email)", value=current_config.get("smtp_user", ""))
        smtp_pass = st.text_input("Contraseña SMTP (App Password)", value=current_config.get("smtp_pass", ""), type="password")
        email_destinatario_alertas = st.text_input("Destinatario de Alertas (To)", value=current_config.get("email_destinatario_alertas", ""), help="Aquí es donde se enviarán las alertas")

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        submitted = st.form_submit_button("Guardar Configuración", type="primary")
    with col_btn2:
        tested = st.form_submit_button("Enviar Correo de Prueba")

if submitted:
    # Validaciones básicas
    if "@" not in email_destinatario_alertas or "@" not in smtp_user:
        st.error("Por favor ingresa correos electrónicos válidos que contengan '@'.")
    else:
        new_data = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "smtp_pass": smtp_pass,
            "email_remitente": email_remitente,
            "email_destinatario_alertas": email_destinatario_alertas
        }
        try:
            response = requests.post(URL_CONFIG_API, json=new_data, timeout=5)
            if response.status_code == 200:
                st.success("Configuración guardada correctamente.")
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error al guardar: {response.json().get('error', 'Desconocido')}")
        except Exception as e:
            st.error(f"Error de conexión al guardar configuración: {e}")

if tested:
    with st.spinner("Enviando correo de prueba... esto puede tardar unos segundos"):
        try:
            res = requests.post(URL_CONFIG_TEST, timeout=10)
            if res.status_code == 200:
                st.success(res.json().get('message', 'Correo enviado.'))
                st.balloons()
            else:
                st.error(f"Error al enviar prueba: {res.json().get('error', 'Verifique sus credenciales')}")
        except Exception as e:
            st.error(f"Fallo de conexión enviando prueba: {e}")

st.divider()

# --- INICIO DE AGREGADO: Configuración de Umbrales (HU-012) ---
st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📊 Configuración de Umbrales de Alertas</h2>', unsafe_allow_html=True)
st.markdown("Define los umbrales personalizados para cada producto (SKU) para la generación de alertas predictivas.")

URL_ALERTS_CONFIG = f"{BASE_URL}/api/v1/alerts/config"

# Get Auth Token
token = st.session_state.get('token')
headers = {"Authorization": f"Bearer {token}"} if token else {}

@st.cache_data(ttl=60)
def fetch_alert_configs():
    try:
        response = requests.get(URL_ALERTS_CONFIG, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error al obtener umbrales: {e}")
    return []

configs_data = fetch_alert_configs()

col_form, col_table = st.columns([1, 2])

with col_form:
    st.markdown('<div class="metric-card" style="padding: 15px; border-top: 4px solid #1E293B;">', unsafe_allow_html=True)
    st.markdown("#### Nuevo/Editar Umbral")
    with st.form("alert_threshold_form"):
        producto_id = st.text_input("ID de Producto (SKU)", placeholder="Ej. SKU-12345")
        umbral_minimo = st.number_input("Umbral Mínimo (Quiebre)", min_value=0, value=10)
        umbral_sobreabastecimiento = st.number_input("Umbral Sobrestock", min_value=1, value=100)
        email_notificacion = st.text_input("Email de Notificación", placeholder="responsable@empresa.com")
        is_active = st.checkbox("Activo", value=True)
        
        submitted_threshold = st.form_submit_button("Guardar Umbral", type="primary")
        
        if submitted_threshold:
            if not producto_id or not email_notificacion:
                st.error("Producto y Email son obligatorios.")
            elif umbral_minimo >= umbral_sobreabastecimiento:
                st.error("El umbral mínimo debe ser menor al de sobrestock.")
            else:
                payload = {
                    "producto_id": producto_id,
                    "umbral_minimo": umbral_minimo,
                    "umbral_sobreabastecimiento": umbral_sobreabastecimiento,
                    "email_notificacion": email_notificacion,
                    "is_active": is_active
                }
                try:
                    res = requests.post(URL_ALERTS_CONFIG, json=payload, headers=headers, timeout=5)
                    if res.status_code == 200:
                        st.toast("Umbral guardado correctamente", icon="✅")
                        fetch_alert_configs.clear() # Limpiar caché para recargar tabla
                        import time
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('error', res.text)}")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with col_table:
    if configs_data:
        import pandas as pd
        df_configs = pd.DataFrame(configs_data)
        # Reordenar columnas para mejor visualización
        cols = ['producto_id', 'umbral_minimo', 'umbral_sobreabastecimiento', 'email_notificacion', 'is_active', 'updated_at']
        df_display = df_configs[[c for c in cols if c in df_configs.columns]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay configuraciones de umbrales activas. Agrega una desde el formulario lateral.")
# --- FIN DE AGREGADO ---

st.divider()

# --- INICIO DE AGREGADO: Reset de Base de Datos ---
st.markdown('<h2 style="color:#DC2626; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">⚠️ Zona de Peligro: Reset de Base de Datos</h2>', unsafe_allow_html=True)
st.markdown("Borra todas las métricas de entrenamiento y los datos de ventas para iniciar de cero o depurar.")

URL_RESET_DB = f"{BASE_URL}/api/v1/reset-db"

# Usamos un formulario o un botón con confirmación visual
st.markdown("""
<div class="metric-card" style="padding: 15px; border-left: 4px solid #DC2626; background-color: #FEF2F2;">
    <h4 style="margin-top:0; color:#991B1B; font-size: 16px;">Limpieza de Tablas</h4>
    <p style="color:#7F1D1D; margin-bottom: 10px; font-size: 14px;">
    <strong>Advertencia:</strong> Esta acción borrará todas las filas de <code>ventas_detalle</code> y <code>entrenamiento</code>. Los cambios son irreversibles.
    </p>
</div>
""", unsafe_allow_html=True)

with st.expander("⚠️ Haz clic aquí para desplegar las opciones de limpieza de la Base de Datos"):
    st.warning("¿Estás absolutamente seguro de que quieres continuar? Esta acción no se puede deshacer.")
    confirm_reset_btn = st.button("Sí, borrar datos (ventas y entrenamiento)", type="primary")

# Creamos el log_box debajo del expander para que sea visible incluso si este se contrae
log_box = st.empty()

if confirm_reset_btn:
    # La lógica se ejecuta si el botón fue presionado. 
    # El log_box fuera del expander mostrará el progreso.
    log_box.info("⏳ Iniciando proceso de borrado...")
    import time
    time.sleep(1) # Pequeña pausa para que se alcance a leer
    log_box.info("⏳ Borrando ventas...\n⏳ Borrando entrenamiento...")
    
    try:
        res = requests.post(URL_RESET_DB, headers=headers, timeout=10)
        if res.status_code == 200:
            log_box.success("✅ Borrando ventas... OK\n✅ Borrando entrenamiento... OK\n\n🎉 ¡Borrado exitoso!")
            st.balloons()
        else:
            try:
                error_msg = res.json().get('error', res.text)
            except:
                error_msg = res.text
            
            # Si el backend sigue devolviendo 404 en HTML, mostramos un error amigable
            if "<html" in error_msg.lower():
                error_msg = "El endpoint /api/v1/reset-db no fue encontrado (Error 404). El servidor backend no tiene la ruta registrada."
            
            log_box.error(f"❌ Error al limpiar: {error_msg}")
    except Exception as e:
        log_box.error(f"❌ Error de conexión: {e}")
# --- FIN DE AGREGADO ---