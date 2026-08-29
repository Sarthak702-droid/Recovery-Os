import asyncio
import smtplib
from email.message import EmailMessage
from app.core.config import get_settings


class SmtpEmailAdapter:
    def available(self) -> bool:
        s = get_settings()
        return bool(s.smtp_host and s.smtp_from)

    async def send_recovery_message(self, *, customer: str, amount_minor: int, currency: str, payment_link: str | None) -> dict:
        if not self.available() or not customer:
            raise RuntimeError("SMTP channel is not configured; no customer message was sent")
        amount = f"₹{amount_minor / 100:,.2f}" if currency == "INR" else f"{amount_minor / 100:.2f} {currency}"
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = get_settings().smtp_from, customer, "Complete your payment securely"
        message.set_content(f"Your payment of {amount} did not complete. You can retry securely here: {payment_link or 'contact merchant support'}. If you have already paid, please ignore this email.")
        def deliver():
            s = get_settings()
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as client:
                client.starttls()
                if s.smtp_username: client.login(s.smtp_username, s.smtp_password)
                client.send_message(message)
        await asyncio.to_thread(deliver)
        return {"message_id": message["Message-ID"] or "smtp-accepted", "status": "sent"}
