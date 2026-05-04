"""Email notification support for alert conditions (e.g. inverter offline)."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends alert emails via SMTP/STARTTLS using configured credentials."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        sender_name: str,
        recipient_email: str,
    ):
        self._smtp_server = smtp_server
        self._smtp_port = smtp_port
        self._sender_email = sender_email
        self._sender_password = sender_password
        self._sender_name = sender_name or sender_email
        self._recipient_email = recipient_email

    @classmethod
    def from_config(cls, email_config) -> "EmailNotifier":
        """Create an EmailNotifier from an EmailConfig dataclass instance."""
        return cls(
            smtp_server=email_config.smtp_server,
            smtp_port=email_config.smtp_port,
            sender_email=email_config.sender_email,
            sender_password=email_config.sender_password,
            sender_name=email_config.sender_name,
            recipient_email=email_config.recipient_email,
        )

    def send_alert(self, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """
        Send an alert email.

        Args:
            subject: Email subject line.
            body: Plain-text message body.
            html_body: Optional HTML version of the body. Falls back to plain text if omitted.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((self._sender_name, self._sender_email))
            msg["To"] = self._recipient_email

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self._smtp_server, self._smtp_port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self._sender_email, self._sender_password)
                smtp.sendmail(self._sender_email, self._recipient_email, msg.as_string())

            logger.info(f"Alert email sent to {self._recipient_email}: {subject}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Email authentication failed. Check SENDER_EMAIL / SENDER_PASSWORD "
                "(use an app password for Gmail/Outlook)."
            )
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending alert email: {e}")
        except OSError as e:
            logger.error(f"Network error sending alert email: {e}")

        return False
