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

# (El resto del contenido se mantiene igual, ya que es neutral)

with st.container(border=True):
    st.subheader("📄 Paso 1: Carga de Datos")
    st.markdown("""
    Navegue a la página **'1_Carga_de_Datos'** en la barra lateral. 
    
    Aquí podrá subir los archivos Excel transaccionales (ej. `Factura_Importacion_PLUS_*.xlsx`). El sistema leerá automáticamente la hoja **'Detalle'** y guardará los datos históricos en la base de datos.
    """)
    st.warning("Nota: Este paso solo es necesario si se dispone de nuevos datos históricos.")

st.write("") # Añadir un espacio

with st.container(border=True):
    st.subheader("🤖 Paso 2: Entrenamiento del Modelo")
    st.markdown("""
    Este paso se realiza **fuera de esta aplicación web** (en el terminal del servidor) y debe ser ejecutado por un administrador técnico.
    """)
    st.info("""
    **Instrucción para el Administrador:**
    Después de cargar nuevos datos en el Paso 1, debe detener el servidor backend y ejecutar el siguiente comando en la terminal para re-entrenar los modelos:
    ```bash
    python -m backend.ml_core.training
    ```
    Una vez completado, reinicie el servidor backend (`python -m backend.app`) para que las nuevas predicciones reflejen la información actualizada.
    """)

st.write("") # Añadir un espacio

with st.container(border=True):
    st.subheader("📈 Paso 3: Visualización de Predicción")
    st.markdown("""
    Navegue a la página **'2_Visualizacion_de_Prediccion'** en la barra lateral.
    
    Ingrese un **SKU (ID de Producto)** y una **fecha futura** para generar un pronóstico de demanda en unidades. Podrá ver la predicción junto al historial de ventas de ese producto.
    """)

