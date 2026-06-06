import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# --- CONFIGURACIÓN DE RUTAS E IMPORTACIONES ---
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

try:
    from frontend.config import get_role_based_sidebar_css
except ImportError:
    def get_role_based_sidebar_css(role: str) -> str: return ""

# --- PROTECCIÓN DE PÁGINA E IDENTIDAD (HU-009) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.switch_page("pages/login.py")
    st.stop()

# --- 1. GESTIÓN DE ACCESOS Y ROLES ---
user_role = st.session_state.user.get('rol', '')
allowed_roles = ['Gerente Administración', 'Gerente General', 'Analista Logística', 'Jefa Almacén']

if user_role == 'Vendedora' or user_role not in allowed_roles:
    st.error("Acceso denegado: Tu perfil comercial no tiene permisos para visualizar el Dashboard Estratégico.")
    st.stop()

# Aplicar CSS de barra lateral basado en el rol
role_css = get_role_based_sidebar_css(user_role)
st.markdown(role_css, unsafe_allow_html=True)

user_name = st.session_state.user.get('nombre', '')
st.title(f"Bienvenido al Dashboard Estratégico, {user_name} 📊")
st.markdown("---")

# --- 5. INTEGRACIÓN CON EL BACKEND Y PLAN DE CONTINGENCIA (MOCKING) ---

@st.cache_data(ttl=300)
def fetch_historical_data(id_producto: str) -> pd.DataFrame:
    """
    HU-009: Extrae datos históricos del backend para la visualización.
    Misión Crítica: Fallback a datos simulados si la API no está disponible.
    """
    try:
        response = requests.get("http://localhost:5000/history", params={"id_producto": id_producto}, timeout=3)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df['fecha'] = pd.to_datetime(df['fecha'])
        return df
    except Exception:
        # Generar DataFrame Mock de Pandas
        fechas = pd.date_range(end=datetime.today(), periods=24, freq='W')
        np.random.seed(hash(id_producto) % 10000)
        base_demand = np.random.randint(50, 150)
        ruido = np.random.normal(0, 10, len(fechas))
        tendencia = np.linspace(0, 20, len(fechas))
        
        return pd.DataFrame({
            'fecha': fechas,
            'cantidad': base_demand + tendencia + ruido,
            'tipo': 'Histórico'
        })

@st.cache_data(ttl=300)
def fetch_prediction_data(id_producto: str, periodo: int) -> Dict[str, Any]:
    """
    HU-009: Extrae predicciones del modelo (MLP/XGBoost) y métricas de error.
    Misión Crítica: Fallback a proyecciones simuladas si falla la conexión.
    """
    try:
        response = requests.get("http://localhost:5000/predict", params={"id_producto": id_producto, "periodo": periodo}, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception:
        # Generar Datos Mock de Predicción
        ultima_fecha = datetime.today()
        fechas_futuras = pd.date_range(start=ultima_fecha + timedelta(days=7), periods=periodo, freq='W')
        
        np.random.seed((hash(id_producto) + periodo) % 10000)
        base_pred = np.random.randint(80, 180)
        ruido = np.random.normal(0, 12, len(fechas_futuras))
        predicciones = base_pred + ruido
        
        limite_sup = predicciones + 15
        limite_inf = predicciones - 15
        riesgo = np.random.randint(5, 35) # Probabilidad simulada de quiebre
        
        return {
            "predicciones": pd.DataFrame({
                "fecha": fechas_futuras,
                "cantidad": predicciones,
                "limite_superior": limite_sup,
                "limite_inferior": limite_inf
            }).to_dict(orient="records"),
            "metricas": {
                "rmse": float(np.random.uniform(8.5, 18.5)),
                "mae": float(np.random.uniform(6.0, 14.0)),
                "mape": float(np.random.uniform(5.0, 15.0)),
                "riesgo_quiebre_stock_porcentaje": riesgo,
                "stock_actual": np.random.randint(20, 200),
                "alerta_sobrestock": "Sí" if predicciones.mean() < 60 else "No"
            }
        }

# Comprobar estado real del servidor para notificar al usuario
backend_status = False
try:
    if requests.get("http://localhost:5000/health", timeout=1).status_code == 200:
        backend_status = True
except:
    pass

if not backend_status:
    st.info("ℹ️ Mostrando datos simulados: El backend no está disponible.")

# --- 2. PANEL DE FILTROS DINÁMICOS (SIDEBAR) ---
st.sidebar.header("🔍 Filtros de Búsqueda")

# Categoría por fuera del formulario para permitir que el selectbox de producto se actualice dinámicamente
categoria = st.sidebar.selectbox("Categoría", ["Repuestos", "Accesorios", "Lubricantes"])

# Catálogo simulado filtrado por categoría
catalogo_productos = {
    "Repuestos": ["REP-001 | Filtro Aceite", "REP-002 | Bujía", "REP-003 | Pastillas Freno"],
    "Accesorios": ["ACC-101 | Funda Asiento", "ACC-102 | Alfombra Goma"],
    "Lubricantes": ["LUB-201 | Aceite Sintético 5W30", "LUB-202 | Refrigerante"]
}

opciones_producto = catalogo_productos.get(categoria, [])

with st.sidebar.form("filtros_dashboard"):
    producto_seleccionado = st.selectbox("Producto (Búsqueda por ID o SKU)", opciones_producto)
    periodo_proyeccion = st.slider("Periodo de Proyección (Semanas)", min_value=1, max_value=12, value=4)
    btn_aplicar = st.form_submit_button("Aplicar Filtros")

# Extraemos solo el ID para enviarlo al API
id_producto = producto_seleccionado.split(" | ")[0] if producto_seleccionado else "UNKNOWN"

# Obtenemos los datos con caché (ya se aplicó el @st.cache_data en las funciones)
df_hist = fetch_historical_data(id_producto)
datos_pred_dict = fetch_prediction_data(id_producto, periodo_proyeccion)

df_pred = pd.DataFrame(datos_pred_dict.get("predicciones", []))
if not df_pred.empty:
    df_pred['fecha'] = pd.to_datetime(df_pred['fecha'])
metricas = datos_pred_dict.get("metricas", {})

# --- 3. KPIs CONSOLIDADOS EN TIEMPO REAL (TOP ROW) ---
rmse_val = metricas.get('rmse', 0)
stock_val = metricas.get('stock_actual', 0)
riesgo_val = metricas.get('riesgo_quiebre_stock_porcentaje', 0)
sobrestock_val = metricas.get('alerta_sobrestock', 'No')

if user_role in ['Gerente General', 'Gerente Administración']:
    col1, col2, col3 = st.columns(3)
    
    costo_unitario = 45.50
    valor_inmovilizado = stock_val * costo_unitario if sobrestock_val == 'Sí' else 0
    costo_quiebre = (riesgo_val / 100) * df_pred['cantidad'].sum() * costo_unitario * 1.5 if not df_pred.empty else 0
    
    with col1:
        st.metric("Precisión del Modelo (RMSE)", f"{rmse_val:.2f}", delta="-1.5 (Optimo)" if rmse_val < 12 else "+2.1 (Revisar)", delta_color="inverse")
    with col2:
        st.metric("Capital Inmovilizado por Sobrestock", f"${valor_inmovilizado:,.2f}")
    with col3:
        st.metric("Costo Estimado por Quiebres de Stock", f"${costo_quiebre:,.2f}")

elif user_role in ['Analista Logística', 'Jefa Almacén']:
    col1, col2, col3 = st.columns(3)
    
    unidades_riesgo = int(df_pred['cantidad'].sum() * (riesgo_val / 100)) if not df_pred.empty else 0
    demanda_promedio_diaria = (df_pred['cantidad'].mean() / 7) if not df_pred.empty and df_pred['cantidad'].mean() > 0 else 1
    dias_inventario = int(stock_val / demanda_promedio_diaria)
    volumen_sobrestock = max(0, int(stock_val - df_pred['cantidad'].sum())) if not df_pred.empty else 0
    
    with col1:
        st.metric("Unidades en Riesgo de Quiebre", f"{unidades_riesgo} unid.")
    with col2:
        st.metric("Días de Inventario Disponible", f"{dias_inventario} días")
    with col3:
        st.metric("Volumen de Sobrestock", f"{volumen_sobrestock} unid.")

st.markdown("---")
st.markdown("### 📈 Histórico vs. Proyección de Demanda")

# --- 4. VISUALIZACIÓN INTERACTIVA (PLOTLY) ---
fig = go.Figure()

# Serie 1 (Histórico): Línea sólida azul
fig.add_trace(go.Scatter(
    x=df_hist['fecha'],
    y=df_hist['cantidad'],
    mode='lines+markers',
    name='Demanda Histórica',
    line=dict(color='#1f77b4', width=2),
    hovertemplate="<b>Fecha:</b> %{x}<br><b>Unidades Reales:</b> %{y:.0f}<extra></extra>"
))

if not df_pred.empty:
    # Serie 2 (Proyección): Línea punteada naranja
    fig.add_trace(go.Scatter(
        x=df_pred['fecha'],
        y=df_pred['cantidad'],
        mode='lines+markers',
        name='Proyección (Modelo)',
        line=dict(color='#ff7f0e', width=2, dash='dash'),
        hovertemplate="<b>Fecha:</b> %{x}<br><b>Proyección:</b> %{y:.1f} unid.<extra></extra>"
    ))
    
    # Sombreado de Bandas de confianza (RMSE)
    if 'limite_superior' in df_pred.columns and 'limite_inferior' in df_pred.columns:
        fig.add_trace(go.Scatter(
            x=pd.concat([df_pred['fecha'], df_pred['fecha'][::-1]]),
            y=pd.concat([df_pred['limite_superior'], df_pred['limite_inferior'][::-1]]),
            fill='toself',
            fillcolor='rgba(255, 127, 14, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Intervalo de Confianza (RMSE)',
            hoverinfo="skip"
        ))

fig.update_layout(
    xaxis_title="Línea de Tiempo",
    yaxis_title="Cantidad (Unidades)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0),
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)
