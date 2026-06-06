import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

def generate_excel_report(df_predictions: pd.DataFrame, kpi_summary: dict, user_name: str, model_version: str = "v1.0-XGBoost-MLP") -> bytes:
    """
    Genera un reporte Excel con múltiples hojas, congelamiento de paneles y autofiltros.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # --- Hoja 1: Resumen KPIs ---
        # Crear un dataframe simple para el resumen
        summary_data = {
            "Metadato": ["Usuario Generador", "Fecha de Generación", "Versión del Modelo"],
            "Valor": [user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), model_version]
        }
        for k, v in kpi_summary.items():
            summary_data["Metadato"].append(k)
            summary_data["Valor"].append(v)
            
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="Resumen_KPIs", index=False)
        
        # Ajustar ancho de columnas en resumen
        worksheet_summary = writer.sheets["Resumen_KPIs"]
        for column_cells in worksheet_summary.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            worksheet_summary.column_dimensions[column_cells[0].column_letter].width = length + 2

        # --- Hoja 2: Detalle Predicciones ---
        df_predictions.to_excel(writer, sheet_name="Detalle_Predicciones", index=False)
        worksheet_detail = writer.sheets["Detalle_Predicciones"]
        
        # Freeze panes en la primera fila (A2 congela la fila 1)
        worksheet_detail.freeze_panes = 'A2'
        
        # AutoFiltros
        if len(df_predictions) > 0:
            worksheet_detail.auto_filter.ref = worksheet_detail.dimensions
            
        # Ajustar ancho de columnas en detalle
        for column_cells in worksheet_detail.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            worksheet_detail.column_dimensions[column_cells[0].column_letter].width = length + 2

    return output.getvalue()

def generate_pdf_report(df_predictions: pd.DataFrame, kpi_summary: dict, user_name: str, model_version: str = "v1.0-XGBoost-MLP", plot_buffer: bytes = None) -> bytes:
    """
    Genera un reporte en PDF con diseño profesional, membrete y tabla de datos.
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F2942'),
        spaceAfter=20,
        alignment=1 # Center
    )
    normal_style = styles["Normal"]

    # --- Título ---
    elements.append(Paragraph("Reporte Predictivo de Inventarios", title_style))
    
    # --- Membrete / Metadatos ---
    metadata_data = [
        # ["[LOGO INSTITUCIONAL]\nImportaciones Centrales Teo S.A.C.", ""],
        ["Importaciones Centrales Teo S.A.C.", ""],
        ["Generado por:", user_name],
        ["Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Versión del Modelo:", model_version]
    ]
    
    metadata_table = Table(metadata_data, colWidths=[200, 300])
    metadata_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748B')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(metadata_table)
    elements.append(Spacer(1, 20))
    
    # --- KPIs ---
    elements.append(Paragraph("Resumen de KPIs", styles['Heading2']))
    kpi_data = [["Indicador", "Valor"]]
    for k, v in kpi_summary.items():
        kpi_data.append([k, str(v)])
        
    kpi_table = Table(kpi_data, colWidths=[200, 150])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2942')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0'))
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))
    
    # --- Imagen (Gráfico) ---
    if plot_buffer:
        try:
            img = Image(io.BytesIO(plot_buffer))
            # Ajustar tamaño preservando aspect ratio (ancho máx 400, alto máx 200)
            img.drawWidth = 400
            img.drawHeight = 200
            elements.append(img)
            elements.append(Spacer(1, 20))
        except Exception as e:
            elements.append(Paragraph(f"No se pudo cargar el gráfico: {str(e)}", normal_style))
            
    # --- Tabla de Datos (Predicciones) ---
    elements.append(Paragraph("Detalle de Predicciones", styles['Heading2']))
    
    # Limitar a 500 filas
    max_rows = 500
    df_pdf = df_predictions.head(max_rows).copy()
    
    if len(df_predictions) > max_rows:
        elements.append(Paragraph(f"<i>Nota: Mostrando las primeras {max_rows} filas. Para ver el detalle completo, descargue el archivo Excel.</i>", normal_style))
        elements.append(Spacer(1, 10))
        
    # Convertir a lista para reportlab
    columns = list(df_pdf.columns)
    data = [columns] + df_pdf.astype(str).values.tolist()
    
    # Calcular ancho de columnas
    col_widths = [min(100, 700 / len(columns))] * len(columns) if len(columns) > 0 else None
    
    data_table = Table(data, repeatRows=1, colWidths=col_widths)
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2942')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(data_table)
    
    doc.build(elements)
    return output.getvalue()
