import smtplib
import os
import socket
import logging
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from backend.database.db_utils import get_config_params

logger = logging.getLogger(__name__)

class EmailProvider(ABC):
    """
    Interfaz base para los proveedores de envío de correos electrónicos.
    Implementa el patrón Strategy.
    """
    
    @abstractmethod
    def send_summary(self, alerts_data: List[Dict[str, Any]], recipient_email: str = None) -> bool:
        """
        Envía un resumen de las alertas por correo electrónico.
        """
        pass

    def _build_html_content(self, alerts_data: List[Dict[str, Any]]) -> str:
        """
        Construye el contenido HTML para el resumen de alertas.
        """
        html = """
        <html>
        <head>
            <style>
                table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .quiebre { color: #d9534f; font-weight: bold; }
                .sobrestock { color: #f0ad4e; font-weight: bold; }
            </style>
        </head>
        <body>
            <h2>Resumen de Alertas de Inventario</h2>
            <p>Se han detectado las siguientes alertas para los próximos días:</p>
            <table>
                <tr>
                    <th>SKU</th>
                    <th>Tipo</th>
                    <th>Mensaje</th>
                    <th>Fecha Proyección</th>
                </tr>
        """

        for alert in alerts_data:
            tipo_class = "quiebre" if alert['tipo'] == 'QUIEBRE' else "sobrestock"
            html += f"""
                <tr>
                    <td>{alert['sku']}</td>
                    <td class="{tipo_class}">{alert['tipo']}</td>
                    <td>{alert['mensaje']}</td>
                    <td>{alert['fecha_proyeccion']}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """
        return html


class SmtpGmailProvider(EmailProvider):
    """
    Implementación del proveedor de correos usando SMTP (ideal para Gmail/Testing).
    Lee la configuración desde la base de datos (tabla configuracion_sistema).
    """
    def send_summary(self, alerts_data: List[Dict[str, Any]], recipient_email: str = None) -> bool:
        # 1. Obtener la configuración dinámica de la base de datos
        config = get_config_params()
        if not config:
            logger.error("No se pudo obtener la configuración de la BD para enviar correo.")
            return False
            
        smtp_host = config.get("smtp_host", "smtp.gmail.com")
        try:
            smtp_port = int(config.get("smtp_port", 587))
        except ValueError:
            smtp_port = 587
            
        smtp_user = config.get("smtp_user", "")
        smtp_pass = config.get("smtp_pass", "")
        email_remitente = config.get("email_remitente", "alertas@predictivo.auto")
        
        # Si no se pasó destinatario explícito, usar el de la BD
        final_recipient = recipient_email if recipient_email else config.get("email_destinatario_alertas")
        
        if not final_recipient:
            logger.warning("No hay destinatario configurado válido para el envío de correos.")
            return False

        if not alerts_data:
            logger.info("No hay alertas para enviar.")
            return False

        # Agrupar alertas por email de notificación (HU-012)
        alerts_by_email = {}
        for alert in alerts_data:
            dest = alert.get("email_notificacion") or final_recipient
            if dest:
                if dest not in alerts_by_email:
                    alerts_by_email[dest] = []
                alerts_by_email[dest].append(alert)

        if not alerts_by_email:
            logger.warning("No se pudo determinar ningún destinatario válido para las alertas.")
            return False

        try:
            # Iniciar conexión SMTP
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
            
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            else:
                logger.warning("Credenciales SMTP no configuradas. El envío podría fallar.")
                
            success_count = 0
            
            # Enviar a cada destinatario sus alertas correspondientes
            for dest, alerts in alerts_by_email.items():
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"⚠️ Resumen de Alertas de Inventario ({len(alerts)} nuevas)"
                msg["From"] = email_remitente
                msg["To"] = dest

                html = self._build_html_content(alerts)
                part = MIMEText(html, "html")
                msg.attach(part)
                
                try:
                    server.sendmail(msg["From"], msg["To"], msg.as_string())
                    logger.info(f"Correo de resumen enviado vía SMTP a {dest} con {len(alerts)} alertas.")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error al enviar a {dest}: {e}")
                    
            server.quit()
            return success_count > 0



        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Error de Autenticación SMTP (Verifica el App Password de Gmail o la BD): {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Error general de SMTP: {e}")
            return False
        except socket.error as e:
            logger.error(f"Error de socket/conexión de red (Rechazado - Errno 111): {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al enviar correo SMTP: {e}", exc_info=True)
            return False


class AwsSesProvider(EmailProvider):
    """
    Implementación del proveedor de correos usando AWS SES (Amazon Simple Email Service).
    Actualmente es un cascarón que se activará en la migración.
    """
    def __init__(self):
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.sender = os.environ.get('AWS_SES_SENDER', 'no-reply@tudominio.com')
        # TODO: self.client = boto3.client('ses', region_name=self.aws_region)

    def send_summary(self, alerts_data: List[Dict[str, Any]], recipient_email: str = None) -> bool:
        if not alerts_data:
            return False
            
        try:
            config = get_config_params()
            final_recipient = recipient_email if recipient_email else config.get("email_destinatario_alertas")
            
            if not final_recipient:
                logger.warning("No hay destinatario configurado válido para el envío de correos.")
                return False
                
            html_body = self._build_html_content(alerts_data)
            subject = f"⚠️ Resumen de Alertas de Inventario ({len(alerts_data)} nuevas)"
            
            logger.info(f"PREPARANDO ENVÍO VÍA AWS SES a {final_recipient} desde {self.sender}")
            
            # TODO: Descomentar e implementar cuando se tenga boto3 y las credenciales de AWS listas
            """
            response = self.client.send_email(
                Destination={'ToAddresses': [final_recipient]},
                Message={
                    'Body': {
                        'Html': {'Charset': "UTF-8", 'Data': html_body}
                    },
                    'Subject': {'Charset': "UTF-8", 'Data': subject},
                },
                Source=self.sender
            )
            logger.info(f"Correo enviado exitosamente vía SES. MessageId: {response['MessageId']}")
            """
            
            # Mock de éxito mientras tanto
            logger.info("Envío simulado vía AWS SES completado con éxito (CASCARÓN).")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar correo vía AWS SES: {e}", exc_info=True)
            return False


class EmailProviderFactory:
    """
    Factory para crear la instancia del proveedor de email configurado en el sistema.
    """
    @staticmethod
    def get_provider() -> EmailProvider:
        provider_name = os.environ.get('EMAIL_PROVIDER', 'SMTP').upper()
        
        if provider_name == 'SES':
            return AwsSesProvider()
        elif provider_name == 'SMTP':
            return SmtpGmailProvider()
        else:
            logger.warning(f"Proveedor de correo '{provider_name}' no soportado. Usando SMTP por defecto.")
            return SmtpGmailProvider()


# --- FUNCIÓN PÚBLICA PARA EL RESTO DEL BACKEND ---

def send_alerts_summary(alerts_data: List[Dict[str, Any]], recipient_email: str = None) -> bool:
    """
    Función de entrada para el envío de alertas. Delega la ejecución al 
    proveedor activo seleccionado vía variables de entorno o BD.
    """
    provider = EmailProviderFactory.get_provider()
    return provider.send_summary(alerts_data, recipient_email)
