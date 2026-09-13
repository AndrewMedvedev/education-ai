from src.core.mail import mail_config
from src.shared.infra.mail import SmtpMailClient

mail_client = SmtpMailClient(
    smtp_port=mail_config.smtp_port,
    smtp_host=mail_config.smtp_host,
    use_tls=mail_config.smtp_use_tls,
)
