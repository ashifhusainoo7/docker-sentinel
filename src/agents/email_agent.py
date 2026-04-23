import logging
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings

logger = logging.getLogger("sentinel.agents.email")


class EmailAgent:
    """Sends HTML crash reports via SMTP (default: Gmail).

    Renders `src/templates/crash_email.html` with Jinja2 then delivers
    through `aiosmtplib.send` with STARTTLS. All delivery errors are
    swallowed — send returns False on any failure.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        timeout_s: float = 15.0,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.timeout_s = timeout_s
        self._env = Environment(
            loader=FileSystemLoader("src/templates"),
            autoescape=select_autoescape(["html"]),
        )

    async def send(
        self, crash_event: dict, analysis: dict, recipient_email: str
    ) -> bool:
        """Returns True on successful SMTP send, False on any failure."""
        try:
            template = self._env.get_template("crash_email.html")
            html = template.render(
                event=crash_event,
                analysis=analysis,
                summary=None,
                dashboard_url=settings.app_url,
            )
            msg = EmailMessage()
            msg["From"] = self.from_email
            msg["To"] = recipient_email
            msg["Subject"] = (
                f"[DockerSentinel] Crash: "
                f"{crash_event.get('container_name', 'unknown')}"
            )
            msg.set_content("View this email in an HTML-capable client.")
            msg.add_alternative(html, subtype="html")

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
                timeout=self.timeout_s,
            )
            return True
        except Exception:
            logger.exception("Email send failed")
            return False
