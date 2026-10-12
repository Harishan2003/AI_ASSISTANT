"""
Friday AI Assistant - Direct Email Dispatch & Attachment Service
Supports direct SMTP email transmission with file attachments,
Outlook command-line dispatch with attachments (/a), and smart browser mail automation.
"""

from __future__ import annotations

import os
import smtplib
import ssl
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        pass

    def get_smtp_config(self) -> Dict[str, Any]:
        """Loads SMTP configuration from environment or user profile."""
        from app.services.command_executor import load_user_profile
        prof = load_user_profile()

        smtp_user = os.getenv("SMTP_EMAIL") or os.getenv("EMAIL_USER") or prof.get("profile", {}).get("email") or prof.get("email") or ""
        smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASS") or os.getenv("EMAIL_PASSWORD") or ""
        smtp_host = os.getenv("SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(os.getenv("SMTP_PORT") or "587")

        return {
            "user": smtp_user.strip(),
            "password": smtp_pass.strip(),
            "host": smtp_host.strip(),
            "port": smtp_port,
            "configured": bool(smtp_user.strip() and smtp_pass.strip())
        }

    def send_email_direct(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        sender_name: str = "Harishan"
    ) -> Tuple[bool, str]:
        """
        Transmits an email directly over SMTP with MIME file attachment.
        """
        cfg = self.get_smtp_config()
        if not cfg["configured"]:
            return False, "SMTP credentials (SMTP_EMAIL and SMTP_PASSWORD) are not configured."

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{cfg['user']}>"
            msg["To"] = recipient.strip()
            msg["Subject"] = subject.strip()

            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Attach file if provided
            if attachment_path and os.path.exists(attachment_path):
                file_p = Path(attachment_path)
                with open(str(file_p), "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {file_p.name}",
                )
                msg.attach(part)

            # Transmit via TLS
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.starttls(context=context)
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["user"], recipient.strip(), msg.as_string())

            att_str = f" with '{Path(attachment_path).name}' attached" if (attachment_path and os.path.exists(attachment_path)) else ""
            return True, f"Email successfully sent directly to {recipient}{att_str} via SMTP!"

        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False, str(e)

    def launch_desktop_client_with_attachment(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Attempts to launch Outlook or native desktop client with attachment attached via /a switch.
        """
        import subprocess
        clean_recipient = recipient.strip()

        # 1. Try Microsoft Outlook natively with /a attachment parameter
        if attachment_path and os.path.exists(attachment_path):
            abs_p = os.path.abspath(attachment_path)
            try:
                # Outlook command line: outlook.exe /c ipm.note /m "<recipient>?subject=<su>&body=<body>" /a "<attachment>"
                mail_param = f"{clean_recipient}?subject={subject}&body={body}" if clean_recipient else f"?subject={subject}&body={body}"
                cmd = f'start outlook.exe /c ipm.note /m "{mail_param}" /a "{abs_p}"'
                subprocess.Popen(cmd, shell=True)
                return True
            except Exception:
                pass

        # 2. Try Thunderbird
        if attachment_path and os.path.exists(attachment_path):
            abs_p = os.path.abspath(attachment_path)
            try:
                cmd = f'start thunderbird -compose "to=\'{clean_recipient}\',subject=\'{subject}\',body=\'{body}\',attachment=\'{abs_p}\'"'
                subprocess.Popen(cmd, shell=True)
                return True
            except Exception:
                pass

        return False


email_service = EmailService()
