import streamlit as st

# --- Configuración de la Página ---
# Esta debe ser la PRIMERA llamada de Streamlit en el script.
st.set_page_config(
    page_title="Sistema Predictivo | Inicio",
    page_icon="📊",  # Ícono para la pestaña del navegador
    layout="wide"    # Usar el ancho completo de la página
)

# --- Barra Lateral (Sidebar) ---
# Contenido profesional y neutral
with st.sidebar:
    st.header("Acerca de la Aplicación")
    st.markdown("""
    Esta plataforma utiliza modelos de Machine Learning para 
    generar pronósticos de demanda y optimizar la gestión 
    de inventario.
    """)
    
    st.divider() # Un separador visual
    
    st.info("Versión 1.0 (MVP)")
    
    st.divider() # Un separador visual
    
    # Asumiendo el nombre de la empresa de la tesis, si no, se puede cambiar
    st.caption("© 2025 Importaciones Centrales Teo. \nTodos los derechos reservados.")

# --- Contenido Principal de la Página ---

# 1. Título y Resumen (Profesionalizado)
st.title("Sistema Predictivo para la Gestión de Inventarios 📊")
st.subheader("Plataforma de Optimización de Stock y Pronóstico de Demanda") # <-- Texto actualizado
st.markdown("""
Esta herramienta aplica un modelo híbrido de Machine Learning (MLP y XGBoost) para pronosticar la demanda futura de productos a nivel de SKU. 
El objetivo es resolver la problemática de gestión de inventarios ineficiente (sobrestock y quiebres de stock), reemplazando el análisis manual por un pronóstico estadístico basado en datos transaccionales.
""") # <-- Texto actualizado

st.divider()

# 2. Guía de Uso
st.header("Guía de Uso del Sistema")
st.markdown("Siga estos pasos para utilizar la aplicación:")

# (Paso 1 no se modifica)
with st.container(border=True):
    st.subheader("📄 Paso 1: Carga de Datos")
    st.markdown("""
    Navegue a la página **'1_Carga_de_Datos'** en la barra lateral. 
    
    Aquí podrá subir los archivos Excel transaccionales (ej. `Factura_Importacion_PLUS_*.xlsx`). El sistema leerá automáticamente la hoja **'Detalle'** y guardará los datos históricos en la base de datos.
    """)
    st.warning("Nota: Este paso solo es necesario si se dispone de nuevos datos históricos.")

st.write("") # Añadir un espacio

# --- INICIO DE LA MODIFICACIÓN ---
# Paso 2 (Actualizado para redirigir a la nueva página de admin)
with st.container(border=True):
    st.subheader("🤖 Paso 2: Administración y Entrenamiento")
    st.markdown("""
    Navegue a la página **'3_Administracion'** en la barra lateral. 
    
    Desde esta sección segura, un administrador puede iniciar el proceso de **re-entrenamiento del modelo**. El sistema utilizará todos los datos cargados hasta la fecha para generar y activar los nuevos modelos de predicción.
    """)
    st.warning("""
    **Advertencia:** Esta acción solo debe ser ejecutada por personal autorizado. 
    El re-entrenamiento puede tardar varios minutos y reemplazará los modelos de predicción actuales en vivo.
    """)
# --- FIN DE LA MODIFICACIÓN ---

st.write("") # Añadir un espacio

# (Paso 3 no se modifica)
with st.container(border=True):
    st.subheader("📈 Paso 3: Visualización de Predicción")
    st.markdown("""
    Navegue a la página **'2_Visualizacion_de_Prediccion'** en la barra lateral.
    
    Ingrese un **SKU (ID de Producto)** y una **fecha futura** para generar un pronóstico de demanda en unidades. Podrá ver la predicción junto al historial de ventas de ese producto.
    """)
