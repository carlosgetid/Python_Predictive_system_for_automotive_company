# TO-DO: Integración de Stock Real para Alertas (HU-007)

## 📌 Contexto y Problema Actual
Actualmente, el cálculo para la Generación de Alertas Automáticas (HU-007) carece de una fuente de datos real para el inventario. Las predicciones del modelo se están contrastando contra datos simulados o inexistentes, ya que la base de datos PostgreSQL no cuenta con una tabla de inventario alimentada con el `stock_actual` y `stock_seguridad`.

## 🚀 Solución Propuesta (Carga Masiva vía Excel)
Reemplazar la data mockeada mediante la implementación de una nueva funcionalidad de Ingesta de Stock. Se construirá una interfaz Drag and Drop en Streamlit que permita al usuario (Supervisor de Inventario) cargar archivos Excel (`.xlsx`) con las cantidades actualizadas por SKU, las cuales se guardarán en la base de datos.

---

## 📋 Lista de Tareas (Checklist)

### 1. Frontend (Streamlit)
- [ ] Crear una vista de "Actualización de Inventario" (o integrarlo en `1_Carga_de_Datos.py`).
- [ ] Implementar el componente `st.file_uploader` (Drag & Drop) restringido a extensiones `.xlsx` y `.xls`.
- [ ] Mostrar una vista previa (Dataframe) de los primeros registros cargados antes de confirmar el envío.
- [ ] Añadir botón de confirmación que envíe el archivo al backend vía request POST.

### 2. Backend (Flask / API)
- [ ] Crear el endpoint `POST /api/inventory/upload`.
- [ ] Validar que el archivo recibido sea un Excel válido.
- [ ] Utilizar `pandas` para leer el archivo y verificar que existan las columnas obligatorias (ej. `id_producto`, `stock_actual`, `stock_seguridad`).

### 3. Base de Datos (`db_utils.py`)
- [ ] Crear el script de migración/DDL para la tabla `inventario` (id_producto, stock_actual, stock_seguridad, ultima_actualizacion).
- [ ] Implementar la función `upsert_inventory_data(df, engine)`: Si el SKU ya existe, actualizar sus cantidades; si no existe, insertarlo.

### 4. Integración Core (HU-007)
- [ ] Refactorizar `backend/services/alert_service.py` (función `run_daily_alert_analysis`).
- [ ] Eliminar los datos mockeados.
- [ ] Hacer que el análisis obtenga dinámicamente el stock cruzando la tabla `inventario` con las predicciones del modelo para calcular el riesgo real de quiebre o sobrestock.
