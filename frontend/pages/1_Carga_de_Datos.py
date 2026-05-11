import streamlit as st
import requests
import os
import logging

from frontend.config import get_setting
from frontend.styles import get_app_css

# --- PROTECCIÓN DE PÁGINA ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos para cargar datos.")
    st.stop()

MOSTRAR_CARGA_MANUAL = get_setting("MOSTRAR_CARGA_MANUAL", True)

st.markdown(get_app_css(), unsafe_allow_html=True)

# ── CSS específico de esta página ──────────────────────────────────────────────
st.markdown("""
<style>
/* Zona de drop */
[data-testid="stFileUploadDropzone"] {
    border: 2px dashed #94A3B8 !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg,#F8FAFC 0%,#EFF6FF 100%) !important;
    box-shadow: none !important;
    min-height: 100px !important;
    transition: border-color .2s, background .2s;
}
[data-testid="stFileUploadDropzone"]:hover {
    border-color: #0F2942 !important;
    background: linear-gradient(135deg,#EFF6FF 0%,#DBEAFE 100%) !important;
    box-shadow: 0 0 0 4px rgba(15,41,66,.07) !important;
}

/* Tabla */
.tbl-header {
    display: flex; align-items: center; gap:8px;
    background: #F1F5F9; border-radius: 8px 8px 0 0;
    padding: 10px 14px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: #0F2942;
    border-bottom: 2px solid #E2E8F0;
}
.tbl-row {
    display: flex; align-items: center; gap:8px;
    padding: 9px 14px;
    border-bottom: 1px solid #F1F5F9;
    background: #fff;
    transition: background .12s;
}
.tbl-row:hover { background: #F8FAFC; }
.tbl-row:last-child { border-radius: 0 0 8px 8px; border-bottom: none; }

/* Badges */
.badge {
    display: inline-flex; align-items: center; gap:4px;
    border-radius: 20px; padding: 3px 12px;
    font-size: 12px; font-weight: 700; white-space: nowrap;
}
.badge-valido    { background:#D1FAE5; color:#065F46; }
.badge-invalido  { background:#FEE2E2; color:#991B1B; }
.badge-procesado { background:#EDE9FE; color:#4C1D95; }
.badge-pendiente { background:#F1F5F9; color:#64748B; }

/* Section title */
.stitle {
    color:#0F2942; font-size:17px; font-weight:700;
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 10px; margin-bottom:16px;
    letter-spacing:-.01em;
}

/* Info box */
.info-box {
    background:#EFF6FF; border:1px solid #BFDBFE;
    border-radius:8px; padding:10px 14px;
    color:#1E40AF; font-size:13px; margin-bottom:12px;
}
</style>
""", unsafe_allow_html=True)

# ── Configuración ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BASE_URL     = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
URL_UPLOAD   = f"{BASE_URL}/upload"
URL_FILES    = f"{BASE_URL}/api/v1/files"
USUARIO_ACTUAL = st.session_state.user.get('username', 'Sistema')

# ── Session state ──────────────────────────────────────────────────────────────
if "uploader_key"      not in st.session_state: st.session_state.uploader_key      = 0
if "queue"             not in st.session_state: st.session_state.queue             = {}
if "deleted_filenames" not in st.session_state: st.session_state.deleted_filenames = set()
if "carga_refresh_key" not in st.session_state: st.session_state.carga_refresh_key = 0

# ── Helpers ────────────────────────────────────────────────────────────────────
def fetch_persisted_files():
    """Consulta los archivos registrados en la BD vía API."""
    try:
        r = requests.get(URL_FILES, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logging.warning(f"No se pudo obtener archivos del backend: {e}")
    return None

def delete_persisted_file(file_id: int):
    """Llama al DELETE del backend para quitar el registro de la BD."""
    try:
        r = requests.delete(f"{URL_FILES}/{file_id}", timeout=8)
        return r.status_code == 200, r.json().get("message", "") if r.ok else r.json().get("error", "")
    except Exception as e:
        return False, str(e)

def badge_html(estado: str, tooltip: str = "") -> str:
    estado_lower = estado.lower()
    labels = {
        "valido":    ("📋", "Válido",    "badge-valido"),
        "aprobado":  ("✅", "Aprobado",  "badge-aprobado"),
        "invalido":  ("❌", "Inválido",  "badge-invalido"),
        "procesado": ("🔬", "Procesado", "badge-procesado"),
    }
    icon, label, cls = labels.get(estado_lower, ("⏳", estado, "badge-pendiente"))
    title = f'title="{tooltip}"' if tooltip else ""
    return f'<span class="badge {cls}" {title}>{icon} {label}</span>'

# ── Cabecera ───────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="color:#0F2942;margin-bottom:4px;">📂 Carga de Datos</h1>',
    unsafe_allow_html=True
)
st.markdown(
    '<p style="color:#64748B;font-size:15px;margin-bottom:20px;">'
    'Gestione los archivos Excel corporativos cargados en el sistema. '
    'Los archivos <b>Válidos</b> pueden ser aprobados para entrenamiento en la vista <b>Ingesta de Datos</b>.</p>',
    unsafe_allow_html=True
)

# ── Modo deshabilitado ─────────────────────────────────────────────────────────
if not MOSTRAR_CARGA_MANUAL:
    st.markdown("""
    <div class="metric-card" style="background-color:#F8FAFC;border-left:5px solid #64748B;">
        <h3 style="color:#0F2942;margin-top:0;">🔒 Modo Manual Deshabilitado</h3>
        <p style="color:#475569;font-size:14px;">
            El sistema opera bajo <b>Ingesta Automatizada (Batch)</b>.
            La carga manual ha sido restringida por el administrador.
        </p>
        <div style="background:#E2E8F0;padding:12px;border-radius:6px;
                    font-family:monospace;color:#334155;font-size:13px;margin:15px 0;">
            📥 Directorio de Entrada: /data_fuente/entrada/
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN A: ARCHIVOS PERSISTIDOS EN EL SISTEMA (fuente: BD)
# ═══════════════════════════════════════════════════════════════════════════════
with st.container(border=True):
    col_title, col_refresh = st.columns([9, 1])
    col_title.markdown('<p class="stitle">📁 Archivos en el Sistema</p>', unsafe_allow_html=True)
    if col_refresh.button("🔄", help="Actualizar lista desde la base de datos", key="btn_refresh"):
        st.session_state.carga_refresh_key += 1  # fuerza refresco real
        st.rerun()

    # carga_refresh_key se usa como «trigger» para que Streamlit
    # siempre refetch los datos cuando cambia
    _ = st.session_state.carga_refresh_key

    st.markdown(
        '<div class="info-box">ℹ️ Esta lista muestra los archivos registrados en la base de datos. '
        'Eliminar un registro <b>no borra</b> los datos de ventas ya guardados en el histórico.</div>',
        unsafe_allow_html=True
    )

    persisted = fetch_persisted_files()

    if persisted is None:
        st.error("⚠️ No se pudo conectar al backend. Verifique que el servidor esté activo.")
    elif len(persisted) == 0:
        st.markdown(
            '<div style="text-align:center;padding:30px 0;color:#94A3B8;font-size:14px;">'
            '📂 No hay archivos registrados. Cargue el primer archivo en la sección inferior.</div>',
            unsafe_allow_html=True
        )
    else:
        # Contadores rápidos
        validos    = sum(1 for f in persisted if f['estado'] == 'valido')
        invalidos  = sum(1 for f in persisted if f['estado'] == 'invalido')
        procesados = sum(1 for f in persisted if f['estado'] == 'procesado')

        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("Total", len(persisted))
        kc2.metric("✅ Válidos",    validos)
        kc3.metric("🔬 Procesados", procesados)
        kc4.metric("❌ Inválidos",  invalidos)

        st.markdown("<br>", unsafe_allow_html=True)

        # Encabezados de la tabla
        h0, h1, h2, h3, h4, h5 = st.columns([3.5, 1.5, 1.8, 1.5, 1.5, 0.7])
        h0.markdown("**Archivo**")
        h1.markdown("**Filas**")
        h2.markdown("**Estado**")
        h3.markdown("**Fecha Carga**")
        h4.markdown("**Cargado por**")
        h5.markdown("**Del.**")
        st.markdown('<hr style="margin:4px 0 4px 0;border-color:#E2E8F0;">', unsafe_allow_html=True)

        for fdata in persisted:
            fid    = fdata['id']
            fname  = fdata['nombre_archivo']
            filas  = fdata.get('filas_guardadas', 0)
            estado = fdata.get('estado', 'pendiente')
            fecha  = fdata.get('fecha_carga', '—')
            owner  = fdata.get('cargado_por', '—')
            msg    = fdata.get('mensaje', '')

            c0, c1, c2, c3, c4, c5 = st.columns([3.5, 1.5, 1.8, 1.5, 1.5, 0.7])

            c0.markdown(
                f'<span style="font-size:13px;color:#1E293B;">📊 <b>{fname}</b></span>',
                unsafe_allow_html=True
            )
            c1.markdown(
                f'<span style="font-size:12px;color:#64748B;">{filas:,}</span>',
                unsafe_allow_html=True
            )
            c2.markdown(badge_html(estado, msg), unsafe_allow_html=True)
            c3.markdown(
                f'<span style="font-size:12px;color:#64748B;">{fecha}</span>',
                unsafe_allow_html=True
            )
            c4.markdown(
                f'<span style="font-size:12px;color:#64748B;">{owner}</span>',
                unsafe_allow_html=True
            )

            if c5.button("🗑️", key=f"del_db_{fid}", help="Eliminar registro de la BD"):
                ok, msg_del = delete_persisted_file(fid)
                if ok:
                    st.toast(f"✅ Registro de '{fname}' eliminado del sistema.", icon="🗑️")
                else:
                    st.toast(f"❌ Error: {msg_del}", icon="⚠️")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN B: CARGAR NUEVOS ARCHIVOS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<p class="stitle">📤 Cargar Nuevos Archivos</p>', unsafe_allow_html=True)

    # Zona de drag & drop
    new_files = st.file_uploader(
        label="Arrastre y suelte archivos .xlsx aquí, o haga clic para seleccionar",
        type=["xlsx"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
        help="Solo se aceptan archivos .xlsx corporativos con la hoja 'Detalle'."
    )

    # Agregar a la cola (sin duplicados ni eliminados)
    if new_files:
        for f in new_files:
            if (f.name not in st.session_state.queue
                    and f.name not in st.session_state.deleted_filenames):
                st.session_state.queue[f.name] = {
                    "file_obj": f,
                    "checked":  True,
                    "size":     f.size,
                    "status":   "pending",
                }

    # ── Cola de archivos por procesar ────────────────────────────────────────
    if st.session_state.queue:
        st.markdown("---")
        n_q = len(st.session_state.queue)
        n_sel = sum(1 for v in st.session_state.queue.values() if v['checked'])
        st.markdown(
            f'<p style="color:#475569;font-size:13px;margin-bottom:8px;">'
            f'<b>{n_q}</b> archivo(s) en cola — <b>{n_sel}</b> seleccionado(s)</p>',
            unsafe_allow_html=True
        )

        # Cabeceras
        hq0, hq1, hq2, hq3 = st.columns([0.5, 5, 1.5, 0.8])
        hq0.markdown('<span style="font-size:11px;font-weight:700;color:#64748B;">✓</span>', unsafe_allow_html=True)
        hq1.markdown('<span style="font-size:11px;font-weight:700;color:#64748B;">ARCHIVO</span>', unsafe_allow_html=True)
        hq2.markdown('<span style="font-size:11px;font-weight:700;color:#64748B;">TAMAÑO</span>', unsafe_allow_html=True)
        hq3.markdown('<span style="font-size:11px;font-weight:700;color:#64748B;">QUITAR</span>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:3px 0 6px 0;border-color:#E2E8F0;">', unsafe_allow_html=True)

        to_remove = []
        for qname in list(st.session_state.queue.keys()):
            qdata = st.session_state.queue[qname]
            c0, c1, c2, c3 = st.columns([0.5, 5, 1.5, 0.8])
            new_chk = c0.checkbox("", value=qdata["checked"], key=f"qchk_{qname}", label_visibility="collapsed")
            st.session_state.queue[qname]["checked"] = new_chk

            size_kb = qdata["size"] / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            c1.markdown(f'<span style="font-size:13px;">📊 <b style="color:#1E293B;">{qname}</b></span>', unsafe_allow_html=True)
            c2.markdown(f'<span style="font-size:12px;color:#64748B;">{size_str}</span>', unsafe_allow_html=True)

            if c3.button("✕", key=f"qrem_{qname}", help="Quitar de la cola"):
                to_remove.append(qname)

        if to_remove:
            for n in to_remove:
                st.session_state.deleted_filenames.add(n)
                del st.session_state.queue[n]
            st.rerun()

        # Botones de control de cola
        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2, _ = st.columns([2, 2, 6])
        with bc1:
            if st.button("🧹 Limpiar cola", use_container_width=True, key="btn_clear_queue"):
                st.session_state.queue             = {}
                st.session_state.deleted_filenames = set()
                st.session_state.uploader_key     += 1
                st.rerun()
        with bc2:
            n_sel_now = sum(1 for v in st.session_state.queue.values() if v['checked'])
            if st.button(
                f"⚙️ Procesar y Guardar ({n_sel_now})",
                disabled=(n_sel_now == 0),
                use_container_width=True,
                key="btn_process"
            ):
                selected = {k: v for k, v in st.session_state.queue.items() if v['checked']}
                total = len(selected)
                ok_count = err_count = 0
                bar = st.progress(0, text="Iniciando...")

                for i, (fname, fdata) in enumerate(selected.items()):
                    bar.progress(int(i / total * 100), text=f"Enviando: {fname} ({i+1}/{total})")
                    try:
                        fobj = fdata["file_obj"]
                        fobj.seek(0)
                        payload = {
                            'file': (
                                fobj.name, fobj.getvalue(),
                                fobj.type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
                        }
                        resp = requests.post(URL_UPLOAD, files=payload, timeout=300)

                        # El backend ya registra en archivos_cargados; solo
                        # necesitamos quitar el archivo de la cola local.
                        if resp.status_code == 201:
                            ok_count += 1
                        else:
                            err_count += 1
                    except requests.exceptions.ConnectionError:
                        err_count += 1
                        st.warning(f"⚠️ Sin conexión al backend para '{fname}'.")
                    except Exception as e:
                        err_count += 1
                        logging.error(f"Error procesando {fname}: {e}", exc_info=True)

                bar.progress(100, text="¡Completado!")

                # Vaciar la cola y resetear el uploader
                st.session_state.queue             = {}
                st.session_state.deleted_filenames = set()
                st.session_state.uploader_key     += 1

                if ok_count:
                    st.success(f"✅ {ok_count} archivo(s) guardado(s) correctamente en la base de datos.")
                if err_count:
                    st.warning(f"⚠️ {err_count} archivo(s) con errores. Revise la sección superior para ver el estado.")

                st.rerun()
    else:
        st.markdown(
            '<div style="text-align:center;padding:16px 0 8px 0;color:#94A3B8;font-size:13px;">'
            '📂 Ningún archivo en cola. Arrastre archivos .xlsx arriba para comenzar.</div>',
            unsafe_allow_html=True
        )