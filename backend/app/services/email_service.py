import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject

            if text_body:
                message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_TLS,
            )
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_email_verification(self, to_email: str, full_name: str, token: str) -> bool:
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = self._email_template(
            title="Verify Your Email",
            preheader="Welcome to Authentra AI - verify your email to get started",
            content=f"""
            <h2>Welcome to Authentra AI, {full_name}!</h2>
            <p>Thank you for registering. Please verify your email address to activate your account.</p>
            <p style="text-align:center;margin:32px 0;">
                <a href="{verify_url}" class="btn">Verify Email Address</a>
            </p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't create this account, you can safely ignore this email.</p>
            """,
        )
        return await self.send_email(to_email, "Verify your Authentra AI account", html)

    async def send_consent_email(
        self,
        to_email: str,
        candidate_name: str,
        company_name: str,
        consent_token: str,
    ) -> bool:
        accept_url = f"{settings.FRONTEND_URL}/consent/{consent_token}?action=accept"
        decline_url = f"{settings.FRONTEND_URL}/consent/{consent_token}?action=decline"
        html = self._email_template(
            title="Background Verification Consent",
            preheader=f"{company_name} is requesting your consent for a background check",
            content=f"""
            <h2>Background Verification Request</h2>
            <p>Dear {candidate_name},</p>
            <p><strong>{company_name}</strong> has initiated a background verification check as part of their hiring process for your application.</p>
            
            <h3>What will be verified:</h3>
            <ul>
                <li>Employment history (dates, titles, companies)</li>
                <li>Educational background (degrees, institutions)</li>
                <li>Public records checks (sanctions lists, public court records)</li>
            </ul>
            
            <h3>Your rights:</h3>
            <ul>
                <li>You have the right to decline this verification</li>
                <li>Your data will be stored securely and deleted per our retention policy</li>
                <li>You may request data export or deletion at any time</li>
                <li>This verification complies with applicable data protection laws</li>
            </ul>
            
            <p style="text-align:center;margin:32px 0;">
                <a href="{accept_url}" class="btn">Accept Verification</a>
                &nbsp;&nbsp;
                <a href="{decline_url}" class="btn btn-secondary">Decline</a>
            </p>
            
            <p style="font-size:12px;color:#888;">By clicking "Accept Verification," you consent to the background check described above. Consent version 1.0.</p>
            """,
        )
        return await self.send_email(
            to_email, f"Background Verification Consent - {company_name}", html
        )

    async def send_verification_request(
        self,
        to_email: str,
        verification_type: str,
        candidate_name: str,
        entity_name: str,
        verification_link: str,
        email_body: str,
    ) -> bool:
        html = self._email_template(
            title=f"{verification_type.title()} Verification Request",
            preheader=f"Employment verification request for {candidate_name}",
            content=f"""
            <h2>{verification_type.title()} Verification Request</h2>
            <pre style="font-family:inherit;white-space:pre-wrap;">{email_body}</pre>
            <p style="text-align:center;margin:32px 0;">
                <a href="{verification_link}" class="btn">Complete Verification Form</a>
            </p>
            <p style="font-size:12px;color:#888;">This request is from Authentra AI on behalf of a hiring organization. Your response is voluntary.</p>
            """,
        )
        return await self.send_email(to_email, f"Employment Verification: {candidate_name}", html)

    async def send_report_ready(self, to_email: str, user_name: str, candidate_name: str, candidate_id: str) -> bool:
        report_url = f"{settings.FRONTEND_URL}/candidates/{candidate_id}"
        html = self._email_template(
            title="Verification Report Ready",
            preheader=f"The background check report for {candidate_name} is ready",
            content=f"""
            <h2>Verification Report Ready</h2>
            <p>Dear {user_name},</p>
            <p>The background verification report for <strong>{candidate_name}</strong> has been completed and is ready for review.</p>
            <p style="text-align:center;margin:32px 0;">
                <a href="{report_url}" class="btn">View Report</a>
            </p>
            """,
        )
        return await self.send_email(to_email, f"Verification Report Ready: {candidate_name}", html)

    def _email_template(self, title: str, preheader: str, content: str) -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ margin:0; padding:0; background:#f4f4f7; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; }}
  .container {{ max-width:600px; margin:32px auto; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#0f172a; padding:24px 32px; }}
  .header h1 {{ margin:0; color:#ffffff; font-size:22px; letter-spacing:-0.5px; }}
  .header span {{ color:#38bdf8; }}
  .body {{ padding:32px; color:#374151; line-height:1.6; }}
  .body h2 {{ color:#111827; margin-top:0; }}
  .body h3 {{ color:#374151; }}
  .btn {{ display:inline-block; background:#0ea5e9; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:6px; font-weight:600; font-size:15px; }}
  .btn-secondary {{ background:#6b7280; }}
  .footer {{ background:#f9fafb; border-top:1px solid #e5e7eb; padding:20px 32px; font-size:12px; color:#9ca3af; }}
  ul {{ padding-left:20px; }}
  li {{ margin-bottom:6px; }}
</style>
</head>
<body>
<span style="display:none;max-height:0;overflow:hidden;">{preheader}</span>
<div class="container">
  <div class="header">
    <h1>Authentra <span>AI</span></h1>
  </div>
  <div class="body">
    {content}
  </div>
  <div class="footer">
    <p>© Authentra AI — Automated Background Verification Platform</p>
    <p>This email was sent because of activity on your account. If you have concerns, please contact support.</p>
  </div>
</div>
</body>
</html>
"""


email_service = EmailService()
