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

def run_daily_alert_analysis():
    """
    Proceso (Job) para analizar predicciones vs stock y generar alertas.
    """
    logger.info("Iniciando análisis diario de alertas de inventario (HU-007)...")
    engine = get_db_engine()
    if not engine:
        logger.error("No se pudo conectar a la BD para el análisis de alertas.")
        return False
        
    skus_data = get_active_skus_with_mock_stock(engine)
    if not skus_data:
        logger.warning("No se encontraron SKUs activos para analizar.")
        return False

    hoy = datetime.date.today()
    alertas_generadas = []
    
    # Limitar para no tardar demasiado si hay miles de SKUs (para MVP)
    max_skus_to_process = 50
    skus_to_process = skus_data[:max_skus_to_process]
    
    for item in skus_to_process:
        sku = item['sku']
        stock_actual = item['stock_actual']
        stock_seguridad = item['stock_seguridad']
        promedio_historico = item['promedio_historico']
        
        # Horizonte de 7 días
        predicciones = []
        for d in range(1, 8):
            fecha_proy = hoy + datetime.timedelta(days=d)
            pred = make_single_prediction(sku, fecha_proy.strftime("%Y-%m-%d"))
            # Si el modelo no puede predecir, asumimos 0
            predicciones.append({
                "dia": d,
                "fecha": fecha_proy,
                "prediccion": pred if pred is not None else 0
            })
            
        # 1. Verificar Quiebre Inminente (48h)
        demanda_48h = sum([p['prediccion'] for p in predicciones[:2]])
        
        if (stock_actual - demanda_48h) <= stock_seguridad:
            mensaje = f"Riesgo de quiebre. Stock: {stock_actual}. Demanda 48h: {demanda_48h}. Stock Seguridad: {stock_seguridad}."
            insert_or_update_alert(
                sku=sku,
                tipo_alerta='QUIEBRE',
                mensaje=mensaje,
                fecha_proyeccion=predicciones[1]['fecha'].strftime("%Y-%m-%d"), # Fecha del día 2
                engine=engine
            )
            alertas_generadas.append({
                "sku": sku, "tipo": "QUIEBRE", "mensaje": mensaje, "fecha_proyeccion": predicciones[1]['fecha'].strftime("%Y-%m-%d")
            })
            
        # 2. Verificar Sobrestock
        # Umbral hardcoded: stock proyectado > 30% del historico total o un multiplo alto.
        # Digamos, si el stock actual supera 30 veces el promedio diario histórico (un mes de stock)
        umbral_sobrestock = promedio_historico * 30
        if stock_actual > umbral_sobrestock:
            mensaje = f"Sobrestock detectado. Stock: {stock_actual}. Umbral máximo: {int(umbral_sobrestock)}."
            insert_or_update_alert(
                sku=sku,
                tipo_alerta='SOBRESTOCK',
                mensaje=mensaje,
                fecha_proyeccion=hoy.strftime("%Y-%m-%d"),
                engine=engine
            )
            alertas_generadas.append({
                "sku": sku, "tipo": "SOBRESTOCK", "mensaje": mensaje, "fecha_proyeccion": hoy.strftime("%Y-%m-%d")
            })

    # Resumen y Notificación
    logger.info(f"Análisis finalizado. Se generaron/actualizaron {len(alertas_generadas)} alertas.")
    
    if alertas_generadas:
        # Enviar el email (no bloqueante en caso de error)
        # El destinatario ahora se obtiene de la base de datos dentro del servicio de email
        send_alerts_summary(alertas_generadas)
        
    return True
