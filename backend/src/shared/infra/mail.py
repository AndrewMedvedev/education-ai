from typing import Any, Protocol

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import html2text
import jinja2

from src.core.settings import TEMPLATES_DIR, settings
from src.shared.domain.exceptions import EmailSendingFailedError

logger = logging.getLogger(__name__)

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


class MailSender(Protocol):
    async def send(
            self,
            to: str | list[str],
            subject: str,
            template_name: str | None = None,
            context: dict[str, Any] | None = None,
            plain_text: str | None = None,
            from_email: str | None = None,
            reply_to: str | None = None,
    ) -> None: ...


class SmtpMailClient:
    def __init__(self, smtp_host: str, smtp_port: int, use_tls: bool = True) -> None:
        self.smtp_config = {"hostname": smtp_host, "port": smtp_port, "use_tls": use_tls}

    async def send(
        self,
        to: str | list[str],
        subject: str,
        template_name: str | None = None,
        context: dict[str, Any] | None = None,
        plain_text: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Отправка письма на почту используя SMTP протокол."""

        from_email = from_email or settings.mail.default_from_email
        recipients = [to] if isinstance(to, list) else to

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(recipients)
        if reply_to is not None:
            msg["Reply-To"] = reply_to

        html_content = None
        if template_name is not None:
            try:
                template = jinja_env.get_template(template_name)
                html_content = template.render(**(context or {}))
            except jinja2.TemplateNotFound as e:
                logger.exception("Template not found")
                raise EmailSendingFailedError(
                    f"Template with name '{template_name}' not found!"
                ) from e

        text_content = plain_text
        if text_content is None and html_content is not None:
            converter = html2text.HTML2Text()
            text_content = converter.handle(html_content)
        if text_content is None and html_content is None:
            error_msg = "Neither the template nor the text of the letter is specified!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        await aiosmtplib.send(msg, recipients=recipients, sender=from_email, **self.smtp_config)
