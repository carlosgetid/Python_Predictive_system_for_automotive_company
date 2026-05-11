import streamlit as st
import sys
import logging
from pathlib import Path
import requests

# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    from frontend.config import get_setting, update_setting, BASE_URL
    from frontend.styles import get_app_css
except ImportError:
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

logging.basicConfig(level=logging.INFO)

# --- PROTECCIÓN DE PÁGINA ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos de configuración.")
    st.stop()

# --- ESTILOS ---
st.markdown(get_app_css(), unsafe_allow_html=True)

st.markdown('<h1 style="color:#0F2942; margin-bottom: 5px;">⚙️ Configuración del Sistema</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748B;">Panel de control para ajustar el comportamiento de la interfaz y funcionalidades del sistema.</p>', unsafe_allow_html=True)
st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- DATOS DE USUARIOS ---
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

user_options_map = {}
for u in users_data:
    username = u.get("username")
    if username:
        label = f"👤 {u.get('nombre', username)} ({u.get('rol', 'Sin Rol')})"
        user_options_map[label] = username

options_list = list(user_options_map.keys())

# --- NAVEGACIÓN POR SIDEBAR (persistente) ---
st.sidebar.markdown("### 🛠️ Panel de Navegación")
selected_tab = st.sidebar.radio(
    "Seleccione una sección:",
    options=[
        "📂 Ingesta de Datos",
        "📧 Notificaciones SMTP",
        "📊 Umbrales de Alerta",
        "⚠️ Reset BD",
        "👥 Gestión de Usuarios"
    ],
    key="config_sidebar_nav"
)

# ============================================================
# SECCIÓN 1: INGESTA DE DATOS
# ============================================================
if selected_tab == "📂 Ingesta de Datos":
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

# ============================================================
# SECCIÓN 2: NOTIFICACIONES SMTP
# ============================================================
elif selected_tab == "📧 Notificaciones SMTP":
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

            current_perfil = current_config.get("perfil_destinatario_alertas", "").strip()
            default_index = 0
            if options_list:
                for i, label in enumerate(options_list):
                    if user_options_map[label] == current_perfil:
                        default_index = i
                        break
                selected_label = st.selectbox(
                    "Destinatario de Alertas",
                    options=options_list,
                    index=default_index,
                    help="Seleccione el perfil del usuario que recibirá las alertas por correo."
                )
                perfil_destinatario_alertas = user_options_map[selected_label]
            else:
                st.warning("⚠️ No hay usuarios disponibles en el sistema.")
                perfil_destinatario_alertas = ""

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            submitted = st.form_submit_button("Guardar Configuración General")
        with col_btn2:
            tested = st.form_submit_button("Enviar Correo de Prueba")

    if submitted:
        if "@" not in smtp_user:
            st.error("Por favor ingresa un correo electrónico válido en el campo Usuario SMTP.")
        else:
            new_data = {
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "smtp_user": smtp_user,
                "smtp_pass": smtp_pass,
                "email_remitente": email_remitente,
                "perfil_destinatario_alertas": perfil_destinatario_alertas
            }
            try:
                response = requests.post(URL_CONFIG_API, json=new_data, timeout=5)
                if response.status_code == 200:
                    st.success("Configuración guardada correctamente.")
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

# ============================================================
# SECCIÓN 3: UMBRALES DE ALERTA
# ============================================================
elif selected_tab == "📊 Umbrales de Alerta":
    st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">📊 Configuración de Umbrales de Alertas</h2>', unsafe_allow_html=True)
    st.markdown("Define los umbrales personalizados para cada producto (SKU). Las alertas se enviarán al destinatario configurado en **Notificaciones SMTP**.")

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

    # Mapa SKU -> config existente para precarga
    existing_configs = {c['producto_id']: c for c in configs_data} if configs_data else {}

    # Selector fuera del form (reactivo): permite precargar valores al editar un SKU existente
    skus_registrados = list(existing_configs.keys())
    sku_edit = st.selectbox(
        "Editar SKU existente (opcional)",
        options=[""] + skus_registrados,
        index=0,
        key="sku_selector_edit",
        help="Selecciona un SKU ya registrado para cargar sus valores guardados y editarlos."
    )
    existing = existing_configs.get(sku_edit, {})

    st.markdown('<div class="metric-card" style="padding: 15px; border-top: 4px solid #1E293B; margin-bottom: 25px;">', unsafe_allow_html=True)
    st.markdown("#### Nuevo/Editar Umbral")

    with st.form("alert_threshold_form"):
        c1, c2 = st.columns(2)
        with c1:
            producto_id = st.text_input(
                "ID de Producto (SKU)",
                value=sku_edit,
                placeholder="Ej. SKU-12345"
            )
            umbral_minimo = st.number_input(
                "Umbral Mínimo (Quiebre)",
                min_value=0,
                value=int(existing.get("umbral_minimo", 10))
            )
            umbral_sobreabastecimiento = st.number_input(
                "Umbral Sobrestock",
                min_value=1,
                value=int(existing.get("umbral_sobreabastecimiento", 100))
            )
        with c2:
            is_active = st.checkbox("Activo", value=bool(existing.get("is_active", True)))
            st.info("📧 Las alertas se enviarán al destinatario configurado en **Notificaciones SMTP**.")

        submitted_threshold = st.form_submit_button("Guardar Umbral", type="primary")

        if submitted_threshold:
            effective_id = producto_id.strip() if producto_id.strip() else sku_edit.strip()
            if not effective_id:
                st.error("El ID de Producto (SKU) es obligatorio.")
            elif umbral_minimo >= umbral_sobreabastecimiento:
                st.error("El umbral mínimo debe ser menor al de sobrestock.")
            else:
                payload = {
                    "producto_id": effective_id,
                    "umbral_minimo": umbral_minimo,
                    "umbral_sobreabastecimiento": umbral_sobreabastecimiento,
                    "is_active": is_active
                }
                try:
                    res = requests.post(URL_ALERTS_CONFIG, json=payload, headers=headers, timeout=5)
                    if res.status_code == 200:
                        st.success(f"Umbral para '{effective_id}' guardado correctamente.")
                        fetch_alert_configs.clear()
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('error', res.text)}")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### Umbrales Registrados")
    if configs_data:
        import pandas as pd
        df_configs = pd.DataFrame(configs_data)
        cols = ['producto_id', 'umbral_minimo', 'umbral_sobreabastecimiento', 'is_active', 'updated_at']
        df_display = df_configs[[c for c in cols if c in df_configs.columns]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay configuraciones de umbrales activas. Agrega una desde el formulario superior.")

# ============================================================
# SECCIÓN 4: RESET BD
# ============================================================
elif selected_tab == "⚠️ Reset BD":
    st.markdown('<h2 style="color:#DC2626; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">⚠️ Zona de Peligro: Reset de Base de Datos</h2>', unsafe_allow_html=True)
    st.markdown("Borra todas las métricas de entrenamiento y los datos de ventas para iniciar de cero o depurar.")

    URL_RESET_DB = f"{BASE_URL}/api/v1/reset-db"
    token = st.session_state.get('token')
    headers = {"Authorization": f"Bearer {token}"} if token else {}

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
                    error_msg = "El endpoint /api/v1/reset-db no fue encontrado (Error 404)."
                log_box.error(f"❌ Error al limpiar: {error_msg}")
        except Exception as e:
            log_box.error(f"❌ Error de conexión: {e}")

# ============================================================
# SECCIÓN 5: GESTIÓN DE USUARIOS
# ============================================================
elif selected_tab == "👥 Gestión de Usuarios":
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
                                    st.success(f"Correo de {u['username']} actualizado.")
                                    fetch_users.clear()
                                else:
                                    st.error(f"Error: {res.json().get('error', 'Desconocido')}")
                            except Exception as e:
                                st.error(f"Fallo al actualizar: {e}")
                st.markdown("---")