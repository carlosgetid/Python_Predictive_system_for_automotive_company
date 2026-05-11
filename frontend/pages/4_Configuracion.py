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
        "📧 Notificaciones SMTP",
        "📊 Umbrales de Alerta",
        "⚠️ Reset BD",
        "👥 Gestión de Usuarios",
        "🚀 Pipelines"
    ],
    key="config_sidebar_nav"
)

# ============================================================
# SECCIÓN 1: NOTIFICACIONES SMTP
# ============================================================
if selected_tab == "📧 Notificaciones SMTP":
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
# SECCIÓN 2: UMBRALES DE ALERTA
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
# SECCIÓN 3: RESET BD
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
# SECCIÓN 4: GESTIÓN DE USUARIOS
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


# ============================================================
# SECCIÓN 5: PIPELINES
# ============================================================
elif selected_tab == "🚀 Pipelines":
    st.markdown('<h2 style="color:#0F2942; font-size: 20px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px;">🚀 Control de Pipelines Automatizados</h2>', unsafe_allow_html=True)
    st.markdown("Monitorea y controla los workers del sistema. Los procesos **persisten incluso si recargues la página**, porque corren de forma independiente del servidor web.")

    URL_PIPELINE_STATUS    = f"{BASE_URL}/api/v1/pipeline/status"
    URL_PIPELINE_START_ALL = f"{BASE_URL}/api/v1/pipeline/start-all"
    URL_PIPELINE_STOP_ALL  = f"{BASE_URL}/api/v1/pipeline/stop-all"

    WORKER_ICONS = {
        "worker_ingestion":  "📥",
        "worker_retraining": "🧠",
        "worker_metrics":    "📊",
        "worker_alerts":     "🔔",
    }

    WORKER_DESCRIPTIONS = {
        "worker_ingestion":  "Aprueba automáticamente los archivos Excel con estado 'Válido', promoviéndolos a 'Aprobado' para el entrenamiento del modelo.",
        "worker_retraining": "Reentrena los modelos de ML con los datos más recientes de la base de datos.",
        "worker_metrics":    "Recopila métricas de rendimiento de los modelos y las guarda en la BD.",
        "worker_alerts":     "Verifica umbrales de inventario y envía alertas por correo si se detectan anomalías.",
    }

    WORKER_DEFAULT_MINUTES = {
        "worker_ingestion":  1,
        "worker_retraining": 3,
        "worker_metrics":    5,
        "worker_alerts":     3,
    }

    # --- Carga del estado ---
    @st.cache_data(ttl=5)
    def fetch_pipeline_status():
        try:
            r = requests.get(URL_PIPELINE_STATUS, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            st.error(f"Error al conectar con el backend: {e}")
        return []

    # --- Botones globales ---
    col_glob1, col_glob2, col_glob3 = st.columns([2, 1, 1])
    with col_glob1:
        st.markdown("")
    with col_glob2:
        if st.button("▶️ Iniciar Todos", use_container_width=True, key="start_all_btn"):
            with st.spinner("Iniciando todos los workers..."):
                try:
                    r = requests.post(URL_PIPELINE_START_ALL, timeout=10)
                    data = r.json()
                    started = [x for x in data.get("results", []) if x.get("status") == "started"]
                    already = [x for x in data.get("results", []) if x.get("status") == "already_running"]
                    errors  = [x for x in data.get("results", []) if x.get("status") == "error"]
                    if started:
                        st.toast(f"✅ {len(started)} worker(s) iniciados", icon="✅")
                    if already:
                        st.toast(f"ℹ️ {len(already)} ya estaban corriendo", icon="ℹ️")
                    if errors:
                        st.toast(f"❌ Errores en {len(errors)} worker(s)", icon="❌")
                    fetch_pipeline_status.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    with col_glob3:
        if st.button("⏹️ Detener Todos", use_container_width=True, key="stop_all_btn"):
            with st.spinner("Deteniendo todos los workers..."):
                try:
                    r = requests.post(URL_PIPELINE_STOP_ALL, timeout=10)
                    data = r.json()
                    stopped = [x for x in data.get("results", []) if x.get("status") == "stopped"]
                    st.toast(f"⏹️ {len(stopped)} worker(s) detenidos", icon="⏹️")
                    fetch_pipeline_status.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    workers_status = fetch_pipeline_status()

    if not workers_status:
        st.warning("⚠️ No se pudo obtener el estado de los pipelines. Verifica que el backend esté activo.")
    else:
        for worker in workers_status:
            wid     = worker["id"]
            label   = worker["label"]
            running = worker["running"]
            pid     = worker.get("pid")
            icon    = WORKER_ICONS.get(wid, "🔧")
            desc    = WORKER_DESCRIPTIONS.get(wid, "")

            # Badge de estado
            if running:
                badge_color  = "#10B981"
                badge_bg     = "#D1FAE5"
                badge_text   = f"🟢 ACTIVO (PID {pid})"
                border_color = "#10B981"
            else:
                badge_color  = "#EF4444"
                badge_bg     = "#FEE2E2"
                badge_text   = "🔴 DETENIDO"
                border_color = "#EF4444"

            # --- Card del worker ---
            st.markdown(f"""
            <div class="metric-card" style="padding: 16px 20px; border-left: 4px solid {border_color}; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <span style="font-size: 22px;">{icon}</span>
                    <strong style="font-size: 16px; color: #0F2942; margin-left: 4px;">{label}</strong>
                    <span style="padding: 3px 10px; border-radius: 20px;
                           background-color: {badge_bg}; color: {badge_color};
                           font-size: 12px; font-weight: 700;">
                        {badge_text}
                    </span>
                </div>
                <p style="color: #64748B; font-size: 13px; margin: 8px 0 0 0;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

            # --- Obtener intervalo actual del backend ---
            try:
                r_iv = requests.get(f"{BASE_URL}/api/v1/pipeline/{wid}/interval", timeout=3)
                current_minutes = r_iv.json().get("minutes", WORKER_DEFAULT_MINUTES.get(wid, 1)) if r_iv.status_code == 200 else WORKER_DEFAULT_MINUTES.get(wid, 1)
            except Exception:
                current_minutes = WORKER_DEFAULT_MINUTES.get(wid, 1)

            # --- Fila de controles: Iniciar | Detener | Frecuencia | Guardar | Logs ---
            col_a, col_b, col_freq, col_save, col_logs = st.columns([1, 1, 1.4, 0.9, 1.6])

            with col_a:
                if not running:
                    if st.button("▶️ Iniciar", key=f"start_{wid}", use_container_width=True):
                        with st.spinner(f"Iniciando {label}..."):
                            try:
                                r = requests.post(f"{BASE_URL}/api/v1/pipeline/{wid}/start", timeout=10)
                                d = r.json()
                                if r.status_code == 200:
                                    st.toast(f"✅ {label} iniciado (PID {d.get('pid')})", icon="✅")
                                else:
                                    st.error(f"Error: {d.get('error', r.text)}")
                                fetch_pipeline_status.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error de conexión: {e}")
                else:
                    st.button("▶️ Iniciado", key=f"start_{wid}", disabled=True, use_container_width=True)

            with col_b:
                if running:
                    if st.button("⏹️ Detener", key=f"stop_{wid}", use_container_width=True):
                        with st.spinner(f"Deteniendo {label}..."):
                            try:
                                r = requests.post(f"{BASE_URL}/api/v1/pipeline/{wid}/stop", timeout=10)
                                d = r.json()
                                if r.status_code == 200:
                                    st.toast(f"⏹️ {label} detenido", icon="⏹️")
                                else:
                                    st.error(f"Error: {d.get('error', r.text)}")
                                fetch_pipeline_status.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error de conexión: {e}")
                else:
                    st.button("⏹️ Detenido", key=f"stop_{wid}", disabled=True, use_container_width=True)

            with col_freq:
                new_minutes = st.number_input(
                    "⏱ Frecuencia (min)",
                    min_value=1,
                    max_value=1440,
                    value=int(current_minutes),
                    step=1,
                    key=f"freq_input_{wid}",
                    help=f"Cada cuántos minutos se ejecuta. Valor actual guardado: {current_minutes} min. El cambio aplica al próximo ciclo sin reiniciar."
                )

            with col_save:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("💾 Guardar", key=f"save_freq_{wid}", use_container_width=True):
                    try:
                        r = requests.post(
                            f"{BASE_URL}/api/v1/pipeline/{wid}/interval",
                            json={"minutes": int(new_minutes)},
                            timeout=5
                        )
                        d = r.json()
                        if r.status_code == 200:
                            st.toast(f"✅ {label}: cada {new_minutes} min", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Error: {d.get('error', r.text)}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")

            with col_logs:
                log_key = f"show_logs_{wid}"
                if log_key not in st.session_state:
                    st.session_state[log_key] = False

                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button(
                    f"{'Ocultar 📄' if st.session_state[log_key] else 'Ver Logs 📄'}",
                    key=f"toggle_log_{wid}",
                    use_container_width=True
                ):
                    st.session_state[log_key] = not st.session_state[log_key]
                    st.rerun()

            # --- Visor de logs expandible ---
            if st.session_state.get(f"show_logs_{wid}", False):
                log_lines_key = f"log_lines_{wid}"
                if log_lines_key not in st.session_state:
                    st.session_state[log_lines_key] = 40

                try:
                    r = requests.get(
                        f"{BASE_URL}/api/v1/pipeline/{wid}/logs",
                        params={"lines": st.session_state[log_lines_key]},
                        timeout=5
                    )
                    if r.status_code == 200:
                        log_data = r.json()
                        logs  = log_data.get("logs", [])
                        total = log_data.get("total_lines", 0)

                        st.markdown(f"""
                        <div style="background-color: #0F172A; border-radius: 8px; padding: 10px 16px;
                                    margin: 6px 0 4px 0; border: 1px solid #1E293B;">
                            <span style="color: #38BDF8; font-size: 12px; font-weight: 700;">
                                📄 LOG: {wid} — Últimas {len(logs)} de {total} líneas
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                        log_text = "\n".join(logs) if logs else "(Sin entradas de log aún)"
                        st.code(log_text, language="bash")

                        c_ref, c_more = st.columns([1, 1])
                        with c_ref:
                            if st.button("🔄 Actualizar Logs", key=f"refresh_log_{wid}", use_container_width=True):
                                st.rerun()
                        with c_more:
                            if st.button("⬇️ Cargar más", key=f"more_log_{wid}", use_container_width=True):
                                st.session_state[log_lines_key] += 40
                                st.rerun()
                    else:
                        st.error(f"Error al obtener logs: {r.json().get('error', r.text)}")
                except Exception as e:
                    st.error(f"Error de conexión al leer logs: {e}")

            st.markdown("<hr style='margin: 10px 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

    # --- Notas informativas ---
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.info("💡 **Persistencia:** Los workers usan `os.setsid()` para correr en su propio grupo de procesos, independiente del servidor web. Recargar la página con Ctrl+R **no los detiene**.")
    st.info("⏱ **Frecuencia:** El nuevo valor aplica al **próximo ciclo de espera** del worker, sin necesidad de reiniciarlo. El worker lee el archivo de configuración al final de cada tarea.")