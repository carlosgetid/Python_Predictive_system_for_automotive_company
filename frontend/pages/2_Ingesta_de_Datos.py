import streamlit as st
import requests
import os
import logging

from frontend.styles import get_app_css

# --- PROTECCIÓN DE PÁGINA ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.stop()

if st.session_state.user['rol'] == 'Vendedora':
    st.error("⛔ Acceso Restringido: Su perfil no tiene permisos para gestionar la ingesta.")
    st.stop()

st.markdown(get_app_css(), unsafe_allow_html=True)

# ── CSS específico ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Badges de estado */
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    border-radius: 20px; padding: 3px 12px;
    font-size: 12px; font-weight: 700; white-space: nowrap;
}
.badge-valido    { background:#DBEAFE; color:#1E40AF; }
.badge-aprobado  { background:#D1FAE5; color:#065F46; }
.badge-procesado { background:#EDE9FE; color:#4C1D95; }
.badge-invalido  { background:#FEE2E2; color:#991B1B; }

/* Sección title */
.stitle {
    color: #0F2942; font-size: 17px; font-weight: 700;
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 10px; margin-bottom: 16px;
}

/* Cards de estadísticas */
.stat-card {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 16px 20px;
    text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.stat-card .num  { font-size: 2rem; font-weight: 800; color: #0F2942; }
.stat-card .lbl  { font-size: 11px; text-transform: uppercase;
                   letter-spacing: .06em; color: #64748B; margin-top: 2px; }

/* Info box */
.info-box {
    background: #EFF6FF; border: 1px solid #BFDBFE;
    border-radius: 8px; padding: 10px 14px;
    color: #1E40AF; font-size: 13px; margin-bottom: 14px;
    line-height: 1.6;
}
.warn-box {
    background: #FFFBEB; border: 1px solid #FDE68A;
    border-radius: 8px; padding: 10px 14px;
    color: #92400E; font-size: 13px; margin-bottom: 14px;
}

/* Tabla cabecera */
.col-lbl {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: #64748B;
}
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
BASE_URL     = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
URL_FILES    = f"{BASE_URL}/api/v1/files"

# ── Helpers ────────────────────────────────────────────────────────────────────
def fetch_all_files():
    try:
        r = requests.get(URL_FILES, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logging.warning(f"Error obteniendo archivos: {e}")
    return None

def set_file_status(file_id: int, new_status: str):
    try:
        r = requests.put(
            f"{URL_FILES}/{file_id}/status",
            json={"estado": new_status},
            timeout=8
        )
        return r.status_code == 200, (r.json().get("message","") if r.ok else r.json().get("error","Error"))
    except Exception as e:
        return False, str(e)

def badge_html(estado: str, tooltip: str = "") -> str:
    labels = {
        "valido":    ("📋", "Válido",    "badge-valido"),
        "aprobado":  ("✅", "Aprobado",  "badge-aprobado"),
        "procesado": ("🔬", "Procesado", "badge-procesado"),
        "invalido":  ("❌", "Inválido",  "badge-invalido"),
    }
    icon, label, cls = labels.get(estado.lower(), ("⏳", estado, "badge-invalido"))
    title = f'title="{tooltip}"' if tooltip else ""
    return f'<span class="badge {cls}" {title}>{icon} {label}</span>'

# ── Session state ──────────────────────────────────────────────────────────────
if "ingesta_selection"   not in st.session_state: st.session_state.ingesta_selection   = {}
if "ingesta_refresh_key" not in st.session_state: st.session_state.ingesta_refresh_key = 0

# ── Cabecera ───────────────────────────────────────────────────────────────────
col_h, col_r = st.columns([10, 1])
col_h.markdown(
    '<h1 style="color:#0F2942;margin-bottom:4px;">⚗️ Ingesta de Datos</h1>',
    unsafe_allow_html=True
)
if col_r.button("🔄", help="Actualizar lista desde la base de datos", key="btn_refresh_ingesta"):
    st.session_state.ingesta_refresh_key += 1
    st.rerun()

# trigger de refresco
_ = st.session_state.ingesta_refresh_key

st.markdown(
    '<p style="color:#64748B;font-size:15px;margin-bottom:20px;">'
    'Apruebe los archivos de ventas que serán utilizados en el próximo ciclo de '
    'entrenamiento del modelo predictivo. Solo los archivos <b>Aprobados</b> '
    'alimentarán el pipeline de re-entrenamiento.</p>',
    unsafe_allow_html=True
)


# ── Flujo de estados ───────────────────────────────────────────────────────────
with st.expander("ℹ️ Flujo de estados de archivos", expanded=False):
    st.markdown("""
    | Estado | Significado |
    |---|---|
    | 📋 **Válido** | El archivo fue procesado y sus datos están en la BD, pero **no participará en el entrenamiento** hasta que sea aprobado |
    | ✅ **Aprobado** | El archivo está habilitado para ser usado en el próximo ciclo de re-entrenamiento del modelo |
    | 🔬 **Procesado** | El archivo ya fue utilizado en al menos un ciclo de entrenamiento |
    | ❌ **Inválido** | El archivo tuvo errores durante la carga y no pudo ser procesado |

    **Para aprobar**: marque los archivos deseados con el checkbox y haga clic en **"Aprobar Seleccionados"**.  
    **Para revertir**: use el botón "↩ Revertir" en cada fila para volver un archivo aprobado a estado Válido.
    """)

# ── Cargar datos del backend ───────────────────────────────────────────────────
all_files = fetch_all_files()

if all_files is None:
    st.error("⚠️ No se pudo conectar al backend. Verifique que el servidor esté activo.")
    st.stop()

# Separar por estado
validos    = [f for f in all_files if f['estado'] == 'valido']
aprobados  = [f for f in all_files if f['estado'] == 'aprobado']
procesados = [f for f in all_files if f['estado'] == 'procesado']
invalidos  = [f for f in all_files if f['estado'] == 'invalido']

# ═══════════════════════════════════════════════════════════════════════════════
#  MÉTRICAS RÁPIDAS
# ═══════════════════════════════════════════════════════════════════════════════
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="num">{len(all_files)}</div>
        <div class="lbl">Total archivos</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-card" style="border-top: 3px solid #3B82F6;">
        <div class="num" style="color:#1D4ED8;">{len(validos)}</div>
        <div class="lbl">📋 Válidos (pendientes)</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-card" style="border-top: 3px solid #10B981;">
        <div class="num" style="color:#065F46;">{len(aprobados)}</div>
        <div class="lbl">✅ Aprobados</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-card" style="border-top: 3px solid #8B5CF6;">
        <div class="num" style="color:#4C1D95;">{len(procesados)}</div>
        <div class="lbl">🔬 Procesados</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN A: ARCHIVOS VÁLIDOS (pendientes de aprobación)
# ═══════════════════════════════════════════════════════════════════════════════
with st.container(border=True):
    st.markdown('<p class="stitle">📋 Archivos Válidos — Pendientes de Aprobación</p>', unsafe_allow_html=True)

    if not validos:
        st.markdown(
            '<div style="text-align:center;padding:24px 0;color:#94A3B8;font-size:14px;">'
            '✅ No hay archivos pendientes de aprobación.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="info-box">Seleccione los archivos que desea habilitar para el entrenamiento '
            'del modelo y haga clic en <b>Aprobar Seleccionados</b>. '
            'Los archivos no seleccionados permanecerán como <b>Válidos</b> y no participarán '
            'en el re-entrenamiento.</div>',
            unsafe_allow_html=True
        )

        # Cabeceras
        hv0, hv1, hv2, hv3, hv4 = st.columns([0.5, 4, 1.5, 1.5, 1.5])
        hv0.markdown('<span class="col-lbl">✓</span>', unsafe_allow_html=True)
        hv1.markdown('<span class="col-lbl">Archivo</span>', unsafe_allow_html=True)
        hv2.markdown('<span class="col-lbl">Filas</span>', unsafe_allow_html=True)
        hv3.markdown('<span class="col-lbl">Fecha Carga</span>', unsafe_allow_html=True)
        hv4.markdown('<span class="col-lbl">Cargado por</span>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:3px 0 6px 0;border-color:#E2E8F0;">', unsafe_allow_html=True)

        # (ingesta_selection ya se inicializó arriba, fuera del if)

        for f in validos:
            fid   = f['id']
            fname = f['nombre_archivo']
            default_chk = st.session_state.ingesta_selection.get(fid, False)

            r0, r1, r2, r3, r4 = st.columns([0.5, 4, 1.5, 1.5, 1.5])
            new_chk = r0.checkbox("", value=default_chk, key=f"sel_v_{fid}", label_visibility="collapsed")
            st.session_state.ingesta_selection[fid] = new_chk

            r1.markdown(
                f'<span style="font-size:13px;">📊 <b style="color:#1E293B;">{fname}</b></span>',
                unsafe_allow_html=True
            )
            r2.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("filas_guardadas", 0):,} filas</span>',
                unsafe_allow_html=True
            )
            r3.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("fecha_carga","—")}</span>',
                unsafe_allow_html=True
            )
            r4.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("cargado_por","—")}</span>',
                unsafe_allow_html=True
            )

        # Botón de aprobación
        st.markdown("<br>", unsafe_allow_html=True)
        ids_seleccionados = [fid for fid, chk in st.session_state.ingesta_selection.items() if chk]
        n_sel = len(ids_seleccionados)

        ba1, ba2, _ = st.columns([3, 3, 4])
        with ba1:
            if st.button(
                f"✅ Aprobar Seleccionados ({n_sel})",
                disabled=(n_sel == 0),
                use_container_width=True,
                key="btn_aprobar"
            ):
                ok_count = 0
                for fid in ids_seleccionados:
                    ok, msg = set_file_status(fid, "aprobado")
                    if ok:
                        ok_count += 1
                    else:
                        st.warning(f"⚠️ Error en archivo #{fid}: {msg}")

                st.session_state.ingesta_selection = {}
                if ok_count:
                    st.success(f"✅ {ok_count} archivo(s) aprobado(s) para el próximo entrenamiento.")
                st.rerun()

        with ba2:
            if st.button("☑️ Seleccionar todos", use_container_width=True, key="btn_sel_all"):
                for f in validos:
                    st.session_state.ingesta_selection[f['id']] = True
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN B: ARCHIVOS APROBADOS (listos para entrenamiento)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<p class="stitle">✅ Archivos Aprobados — Listos para Entrenamiento</p>', unsafe_allow_html=True)

    if not aprobados:
        st.markdown(
            '<div style="text-align:center;padding:24px 0;color:#94A3B8;font-size:14px;">'
            '📋 Ningún archivo aprobado aún. Apruebe archivos en la sección superior.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="info-box" style="background:#F0FDF4;border-color:#BBF7D0;color:#065F46;">'
            f'<b>{len(aprobados)}</b> archivo(s) listos para el próximo ciclo de re-entrenamiento. '
            'El pipeline <b>Reentrenamiento ML</b> y el botón manual en Administración '
            'utilizarán estos archivos como fuente de datos.</div>',
            unsafe_allow_html=True
        )

        # Cabeceras
        ha0, ha1, ha2, ha3, ha4, ha5 = st.columns([3.5, 1.5, 1.5, 1.5, 1.5, 1.2])
        ha0.markdown('<span class="col-lbl">Archivo</span>', unsafe_allow_html=True)
        ha1.markdown('<span class="col-lbl">Filas</span>', unsafe_allow_html=True)
        ha2.markdown('<span class="col-lbl">Estado</span>', unsafe_allow_html=True)
        ha3.markdown('<span class="col-lbl">Fecha Carga</span>', unsafe_allow_html=True)
        ha4.markdown('<span class="col-lbl">Cargado por</span>', unsafe_allow_html=True)
        ha5.markdown('<span class="col-lbl">Revertir</span>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:3px 0 6px 0;border-color:#E2E8F0;">', unsafe_allow_html=True)

        for f in aprobados:
            fid   = f['id']
            fname = f['nombre_archivo']
            r0, r1, r2, r3, r4, r5 = st.columns([3.5, 1.5, 1.5, 1.5, 1.5, 1.2])

            r0.markdown(
                f'<span style="font-size:13px;">📊 <b style="color:#1E293B;">{fname}</b></span>',
                unsafe_allow_html=True
            )
            r1.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("filas_guardadas", 0):,}</span>',
                unsafe_allow_html=True
            )
            r2.markdown(badge_html("aprobado"), unsafe_allow_html=True)
            r3.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("fecha_carga","—")}</span>',
                unsafe_allow_html=True
            )
            r4.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("cargado_por","—")}</span>',
                unsafe_allow_html=True
            )
            if r5.button("↩ Revertir", key=f"rev_{fid}", help="Devolver a estado Válido"):
                ok, msg = set_file_status(fid, "valido")
                if ok:
                    st.toast(f"↩ '{fname}' revertido a Válido.", icon="📋")
                else:
                    st.toast(f"❌ Error: {msg}", icon="⚠️")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN C: ARCHIVOS YA PROCESADOS (histórico)
# ═══════════════════════════════════════════════════════════════════════════════
if procesados:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(f"🔬 Archivos ya Procesados en entrenamientos anteriores ({len(procesados)})", expanded=False):
        hp0, hp1, hp2, hp3 = st.columns([4, 1.5, 1.8, 1.5])
        hp0.markdown('<span class="col-lbl">Archivo</span>', unsafe_allow_html=True)
        hp1.markdown('<span class="col-lbl">Filas</span>', unsafe_allow_html=True)
        hp2.markdown('<span class="col-lbl">Fecha Carga</span>', unsafe_allow_html=True)
        hp3.markdown('<span class="col-lbl">Cargado por</span>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:3px 0 6px 0;border-color:#E2E8F0;">', unsafe_allow_html=True)

        for f in procesados:
            r0, r1, r2, r3 = st.columns([4, 1.5, 1.8, 1.5])
            r0.markdown(
                f'<span style="font-size:13px;color:#6D28D9;">🔬 {f["nombre_archivo"]}</span>',
                unsafe_allow_html=True
            )
            r1.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("filas_guardadas",0):,}</span>',
                unsafe_allow_html=True
            )
            r2.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("fecha_carga","—")}</span>',
                unsafe_allow_html=True
            )
            r3.markdown(
                f'<span style="font-size:12px;color:#64748B;">{f.get("cargado_por","—")}</span>',
                unsafe_allow_html=True
            )
