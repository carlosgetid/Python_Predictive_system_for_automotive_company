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

URL_USERS_API = f"{BASE_URL}/api/v1/users"

@st.cache_data(ttl=30)
def fetch_users():
    try:
        response = requests.get(URL_USERS_API, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error al obtener usuarios: {e}")
    return []

users_data = fetch_users()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 Ingesta de Datos", 
    "📧 Notificaciones SMTP", 
    "📊 Umbrales de Alerta", 
    "⚠️ Reset BD",
    "👥 Gestión de Usuarios"
])

with tab1:
    # --- SECCIÓN: CONTROL DE INGESTA ---
    st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📂 Control de Ingesta de Datos</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
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
        current_state = get_setting("MOSTRAR_CARGA_MANUAL", True)
        
        new_state = st.toggle("Estado", value=current_state, key="toggle_manual")
    
        if new_state != current_state:
            if update_setting("MOSTRAR_CARGA_MANUAL", new_state):
                st.toast(f"Configuración guardada: {'Habilitado' if new_state else 'Deshabilitado'}", icon="✅")
                logging.info(f"Configuración MOSTRAR_CARGA_MANUAL cambiada a {new_state}")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Error al guardar en settings.json")
    
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

with tab2:
    # --- SECCIÓN: Notificaciones y Alertas (SMTP) ---
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
            
            # Preparar opciones para el selectbox de destinatarios basado en perfiles de usuario
            user_options_map = {}
            for u in users_data:
                correo = u.get("correo_electronico")
                if correo: # Solo mostrar usuarios con correo registrado
                    label = f"👤 {u.get('nombre', u.get('username'))} ({u.get('rol', 'Sin Rol')})"
                    user_options_map[label] = correo
            
            options_list = list(user_options_map.keys())
            
            current_email = current_config.get("email_destinatario_alertas", "")
            default_index = 0
            
            if options_list:
                for i, label in enumerate(options_list):
                    if user_options_map[label] == current_email:
                        default_index = i
                        break
                
                selected_label = st.selectbox(
                    "Destinatario de Alertas (Perfil de Usuario)",
                    options=options_list,
                    index=default_index,
                    help="Seleccione el perfil del usuario que recibirá las alertas por correo."
                )
                email_destinatario_alertas = user_options_map[selected_label]
            else:
                st.warning("⚠️ No hay usuarios con correo registrado. Ve a 'Gestión de Usuarios' para agregar correos.")
                email_destinatario_alertas = ""
    
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            submitted = st.form_submit_button("Guardar Configuración", type="primary")
        with col_btn2:
            tested = st.form_submit_button("Enviar Correo de Prueba")
    
    if submitted:
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

with tab3:
    # --- SECCIÓN: Configuración de Umbrales ---
    st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📊 Configuración de Umbrales de Alertas</h2>', unsafe_allow_html=True)
    st.markdown("Define los umbrales personalizados para cada producto (SKU) para la generación de alertas predictivas.")
    
    URL_ALERTS_CONFIG = f"{BASE_URL}/api/v1/alerts/config"
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
                            fetch_alert_configs.clear()
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
            cols = ['producto_id', 'umbral_minimo', 'umbral_sobreabastecimiento', 'email_notificacion', 'is_active', 'updated_at']
            df_display = df_configs[[c for c in cols if c in df_configs.columns]]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No hay configuraciones de umbrales activas. Agrega una desde el formulario lateral.")

with tab4:
    # --- SECCIÓN: Reset de Base de Datos ---
    st.markdown('<h2 style="color:#DC2626; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">⚠️ Zona de Peligro: Reset de Base de Datos</h2>', unsafe_allow_html=True)
    st.markdown("Borra todas las métricas de entrenamiento y los datos de ventas para iniciar de cero o depurar.")
    
    URL_RESET_DB = f"{BASE_URL}/api/v1/reset-db"
    
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
    
    log_box = st.empty()
    
    if confirm_reset_btn:
        log_box.info("⏳ Iniciando proceso de borrado...")
        import time
        time.sleep(1)
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
                if "<html" in error_msg.lower():
                    error_msg = "El endpoint /api/v1/reset-db no fue encontrado (Error 404). El servidor backend no tiene la ruta registrada."
                log_box.error(f"❌ Error al limpiar: {error_msg}")
        except Exception as e:
            log_box.error(f"❌ Error de conexión: {e}")

with tab5:
    # --- SECCIÓN: Gestión de Usuarios ---
    st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">👥 Gestión de Usuarios</h2>', unsafe_allow_html=True)
    st.markdown("Visualiza y administra los datos de los usuarios registrados, incluyendo su correo electrónico para notificaciones.")
    
    URL_USERS_API_LOCAL = f"{BASE_URL}/api/v1/users"
    
    if not users_data:
        st.info("No se encontraron usuarios en la base de datos.")
    else:
        for u in users_data:
            with st.container():
                st.markdown(f"#### 👤 {u.get('nombre', 'Sin Nombre')} ({u.get('username', 'N/A')})")
                col_info, col_edit = st.columns([1, 2])
                with col_info:
                    st.markdown(f"**Rol:** {u.get('rol', 'N/A')}")
                with col_edit:
                    with st.form(f"form_user_{u['id']}", border=False):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            new_email = st.text_input(
                                "Correo Registrado", 
                                value=u.get('correo_electronico', ''), 
                                key=f"email_{u['id']}",
                                label_visibility="collapsed",
                                placeholder="Escribe el correo aquí...",
                                type="password"
                            )
                        with c2:
                            submitted_email = st.form_submit_button("Guardar Correo", type="secondary")
                        
                        if submitted_email:
                            try:
                                url_update = f"{URL_USERS_API_LOCAL}/{u['id']}/email"
                                res = requests.put(url_update, json={"correo_electronico": new_email}, timeout=5)
                                if res.status_code == 200:
                                    st.toast(f"Correo de {u['username']} actualizado", icon="✅")
                                    fetch_users.clear()
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {res.json().get('error', 'Desconocido')}")
                            except Exception as e:
                                st.error(f"Fallo al actualizar: {e}")
                st.markdown("---")