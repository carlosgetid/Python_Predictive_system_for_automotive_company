import streamlit as st
import requests
import pandas as pd # --- NUEVO: Necesario para gráficos
import os
import sys
from pathlib import Path

# [NUEVO] Motor de estilos
from frontend.styles import get_app_css


# --- CONFIGURACIÓN DE RUTAS (Path Fix) ---
# Agregamos la raíz del proyecto al sys.path para importar config
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# --- IMPORTACIÓN DE CONFIGURACIÓN ---
try:
    # Intentamos importar del archivo centralizado
    from frontend.config import URL_RETRAIN, BASE_URL
    # Construimos la URL de métricas basada en la BASE_URL importada
    URL_METRICS = f"{BASE_URL}/api/v1/metrics"
except ImportError:
    # Fallback por si falla el import
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.getenv("BACKEND_PORT", "5000")
    BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    URL_RETRAIN = f"{BASE_URL}/api/v1/trigger_retraining"
    URL_METRICS = f"{BASE_URL}/api/v1/metrics"

# --- PROTECCIÓN DE PÁGINA (Login Required + RBAC) ---
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Acceso no autorizado. Por favor vaya al Inicio e inicie sesión.")
    st.switch_page("pages/login.py")

# Validación de Rol: Bloquear acceso a "Vendedora"
if st.session_state.user['rol'] == 'Vendedora':
    st.switch_page("pages/error.py")
# ----------------------------------------------------

# ----------------------------------------------------

# [NUEVO] Inyectar CSS Global
st.markdown(get_app_css(), unsafe_allow_html=True)

# [NUEVO] Encabezado Corporativo
st.markdown('<h1 style="color:#0F2942; margin-bottom: 5px;">🛡️ Panel de Administración</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="color:#64748B;">Centro de comando para operaciones críticas y monitoreo de rendimiento del sistema.</p>', 
    unsafe_allow_html=True
)
    
# Contenedor para la acción de re-entrenamiento (Custom Critical Card)
st.markdown(
    """
    <div class="metric-card" style="border-left: 5px solid #EF4444; margin-bottom: 30px;">
    <h3 style="color:#0F2942; font-size: 18px; margin-top: 0;">🤖 Re-entrenamiento del Modelo</h3>
    """, unsafe_allow_html=True
)
st.markdown("""
Presione este botón para forzar al sistema a re-entrenar los modelos de predicción (MLP y XGBoost) 
utilizando **todos los datos** actualmente disponibles en la base de datos `ventas_historicas`.
""")
st.warning("""
**Advertencia:** Esta operación es intensiva y no se puede deshacer.
1.  Puede tardar varios minutos en completarse.
2.  Reemplazará los modelos actuales que están en producción.
3.  Se recomienda realizar esta acción solo después de una carga de datos significativa.
""")

# El botón de re-entrenamiento
if st.button("Iniciar Re-entrenamiento del Modelo", type="primary", use_container_width=True):
    try:
        # Mostrar un spinner mientras el backend trabaja
        with st.spinner("Iniciando re-entrenamiento... Esto puede tardar varios minutos. Por favor, no cierre esta ventana."):
            
            # Llamar al nuevo endpoint del backend
            # Usamos un timeout largo (600 segundos = 10 minutos) porque el entrenamiento puede tardar
            response = requests.post(URL_RETRAIN, timeout=600)

            # Manejar la respuesta del backend
            if response.status_code == 200:
                st.success(f"✅ ¡Re-entrenamiento completado con éxito!")
                st.json(response.json()) # Mostrar el JSON de respuesta (que tendrá el mensaje y métricas)
            else:
                # Mostrar el error devuelto por el backend
                error_msg = response.json().get('error', 'Error desconocido del backend.')
                st.error(f"Error {response.status_code}: {error_msg}")
    
    except requests.exceptions.ConnectionError:
        st.error(f"Error de Conexión: No se pudo conectar al backend en {URL_RETRAIN}. ¿Está el backend (python -m backend.app) corriendo?")
    except requests.exceptions.Timeout:
        st.error("Error: La solicitud de re-entrenamiento superó el tiempo límite (10 minutos). El servidor puede seguir entrenando en segundo plano.")
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al contactar el backend: {e}")

# [NUEVO] Cerrar el div de la tarjeta de re-entrenamiento
st.markdown("</div>", unsafe_allow_html=True)
# --- SECCIÓN NUEVA: MONITOREO DE MÉTRICAS (HU-011) ---
st.markdown('<br><br>', unsafe_allow_html=True) # Espaciador
st.markdown('<h2 style="color:#0F2942; font-size: 24px;">📊 Monitoreo de Rendimiento del Modelo</h2>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748B;">Historial de precisión (MAE/RMSE) registrado tras cada re-entrenamiento.</p>', unsafe_allow_html=True)

# Botón para refrescar datos manualmente
if st.button("🔄 Actualizar Gráficos de Rendimiento"):
    try:
        with st.spinner("Obteniendo historial de métricas..."):
            response = requests.get(URL_METRICS, timeout=10)
            
        if response.status_code == 200:
            data = response.json().get("metrics", [])
            
            if data:
                # Convertir a DataFrame para graficar
                df_metrics = pd.DataFrame(data)
                
                # Convertir fecha a objeto datetime para que el gráfico la entienda
                if 'fecha_registro' in df_metrics.columns:
                    df_metrics['fecha_registro'] = pd.to_datetime(df_metrics['fecha_registro'])

                # 1. Gráfico de Líneas (Evolución del Error)
                st.subheader("Evolución del Error (MAE y RMSE)")
                st.caption("Nota: Valores más bajos indican mejor precisión.")
                
                # Usamos 'fecha_registro' como eje X
                chart_data = df_metrics.set_index('fecha_registro')[['mae', 'rmse']]
                st.line_chart(chart_data)

                # 2. Tabla de Datos Recientes
                st.subheader("Registros Detallados")
                # Mostrar primero lo más reciente
                st.dataframe(
                    df_metrics.sort_values(by='fecha_registro', ascending=False),
                    use_container_width=True
                )
            else:
                st.info("Aún no hay métricas registradas. Ejecute un re-entrenamiento para generar el primer punto de datos.")
        else:
            st.error(f"Error al obtener métricas del servidor: {response.text}")

    except requests.exceptions.ConnectionError:
        st.error("No se pudo conectar con el servidor para obtener las métricas.")
    except Exception as e:
        st.error(f"Error inesperado al procesar las métricas: {e}")