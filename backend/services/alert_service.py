import logging
import datetime
import pandas as pd
from sqlalchemy import text
from backend.database.db_utils import get_db_engine, insert_or_update_alert
from backend.ml_core.predict import make_single_prediction
from backend.services.email_service import send_alerts_summary
import os

logger = logging.getLogger(__name__)

def get_active_skus_with_mock_stock(engine):
    """
    Obtiene los SKUs activos de ventas_detalle.
    Como no hay tabla de inventario real, mockea el stock actual y el de seguridad.
    También obtiene el promedio histórico de ventas diarias.
    """
    if engine is None: return []
    
    # Obtenemos SKUs distintos y su promedio de ventas histórico
    query = text("""
        SELECT id_producto, AVG(cantidad_vendida) as prom_ventas
        FROM ventas_detalle
        GROUP BY id_producto
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            skus_data = []
            for row in result:
                # Mockeando datos de inventario
                promedio = float(row[1]) if row[1] is not None else 10.0
                
                # Para que se generen algunas alertas de quiebre y otras de sobrestock,
                # usamos un stock basado en el promedio.
                import random
                mock_stock = int(promedio * random.choice([0.5, 2.0, 50.0])) # Algunos muy bajos, otros normales, otros muy altos
                
                skus_data.append({
                    "sku": str(row[0]),
                    "stock_actual": mock_stock,
                    "stock_seguridad": int(promedio * 0.5), # Stock de seguridad del 50% de la venta promedio
                    "promedio_historico": promedio
                })
            return skus_data
    except Exception as e:
        logger.error(f"Error obteniendo SKUs activos: {e}")
        return []

from backend.database.db_utils import get_alert_configs
import numpy as np

class AlertEvaluator:
    """
    Evaluador de alertas de inventario (HU-012).
    Utiliza operaciones vectorizadas con Pandas para garantizar SLA < 3 segundos.
    """
    def __init__(self, engine):
        self.engine = engine

    def evaluate(self):
        skus_data = get_active_skus_with_mock_stock(self.engine)
        if not skus_data:
            logger.warning("No se encontraron SKUs activos para analizar.")
            return []

        # Obtener configuraciones personalizadas
        configs = get_alert_configs(self.engine, limit=100000)
        df_configs = pd.DataFrame(configs) if configs else pd.DataFrame(columns=['producto_id', 'umbral_minimo', 'umbral_sobreabastecimiento', 'email_notificacion', 'is_active'])
        if not df_configs.empty:
            df_configs = df_configs[df_configs['is_active'] == True]

        # Limitar para no tardar demasiado si hay miles de SKUs (para MVP y rapidez)
        df_skus = pd.DataFrame(skus_data[:50])

        # Join con configuraciones
        if not df_configs.empty:
            df_merged = df_skus.merge(df_configs, left_on='sku', right_on='producto_id', how='left')
        else:
            df_merged = df_skus.copy()
            df_merged['umbral_minimo'] = np.nan
            df_merged['umbral_sobreabastecimiento'] = np.nan
            df_merged['email_notificacion'] = None

        # Rellenar con defaults si no hay config
        df_merged['umbral_minimo'] = df_merged['umbral_minimo'].fillna(df_merged['stock_seguridad']).astype(int)
        df_merged['umbral_sobreabastecimiento'] = df_merged['umbral_sobreabastecimiento'].fillna(df_merged['promedio_historico'] * 30).astype(int)

        hoy = datetime.date.today()
        demanda_48h_list = []
        
        # Obtener predicciones
        for sku in df_merged['sku']:
            d48 = 0
            for d in range(1, 3):
                fecha_proy = hoy + datetime.timedelta(days=d)
                pred = make_single_prediction(sku, fecha_proy.strftime("%Y-%m-%d"))
                d48 += pred if pred is not None else 0
            demanda_48h_list.append(d48)

        df_merged['demanda_48h'] = demanda_48h_list
        df_merged['stock_proyectado'] = df_merged['stock_actual'] - df_merged['demanda_48h']

        # Vectorización estricta para evaluación de umbrales
        mask_quiebre = df_merged['stock_proyectado'] <= df_merged['umbral_minimo']
        mask_sobrestock = df_merged['stock_actual'] > df_merged['umbral_sobreabastecimiento']

        alertas_generadas = []

        # Iterar solo sobre los casos positivos
        for _, row in df_merged[mask_quiebre].iterrows():
            email_notif = row.get('email_notificacion')
            if pd.isna(email_notif): email_notif = None
            
            mensaje = f"Riesgo de quiebre. Stock: {row['stock_actual']}. Demanda esperada: {row['demanda_48h']}. Proyectado: {row['stock_proyectado']}. Umbral: {row['umbral_minimo']}."
            fecha_str = (hoy + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
            insert_or_update_alert(row['sku'], 'QUIEBRE', mensaje, fecha_str, self.engine)
            alertas_generadas.append({
                "sku": row['sku'], "tipo": "QUIEBRE", "mensaje": mensaje, 
                "fecha_proyeccion": fecha_str, "email_notificacion": email_notif
            })

        for _, row in df_merged[mask_sobrestock & ~mask_quiebre].iterrows():
            email_notif = row.get('email_notificacion')
            if pd.isna(email_notif): email_notif = None
            
            mensaje = f"Sobrestock detectado. Stock: {row['stock_actual']}. Demanda esperada: {row['demanda_48h']}. Proyectado: {row['stock_proyectado']}. Umbral máximo: {row['umbral_sobreabastecimiento']}."
            fecha_str = hoy.strftime("%Y-%m-%d")
            insert_or_update_alert(row['sku'], 'SOBRESTOCK', mensaje, fecha_str, self.engine)
            alertas_generadas.append({
                "sku": row['sku'], "tipo": "SOBRESTOCK", "mensaje": mensaje, 
                "fecha_proyeccion": fecha_str, "email_notificacion": email_notif
            })

        return alertas_generadas

def run_daily_alert_analysis():
    """
    Proceso (Job) para analizar predicciones vs stock y generar alertas.
    """
    logger.info("Iniciando análisis diario de alertas de inventario (HU-007 & HU-012)...")
    engine = get_db_engine()
    if not engine:
        logger.error("No se pudo conectar a la BD para el análisis de alertas.")
        return False
        
    evaluator = AlertEvaluator(engine)
    alertas_generadas = evaluator.evaluate()

    # Resumen y Notificación
    logger.info(f"Análisis finalizado. Se generaron/actualizaron {len(alertas_generadas)} alertas.")
    
    if alertas_generadas:
        # Aquí enviaríamos correos directos a los interesados o al default
        # Para el MVP lo enviamos al summary general.
        send_alerts_summary(alertas_generadas)
        
    return True
