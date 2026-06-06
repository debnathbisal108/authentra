import asyncio
import logging
from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.followup_tasks.send_followup_reminders")
def send_followup_reminders():
    return run_async(_send_followups_async())


async def _send_followups_async():
    from app.db.session import AsyncSessionLocal
    from app.models.models import VerificationRequest, VerificationStatus
    from app.services.email_service import email_service
    from app.core.config import settings
    from sqlalchemy import select, and_

    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # Find requests that were sent 3 days ago and haven't been replied to
        three_days_ago = now - timedelta(days=3)
        seven_days_ago = now - timedelta(days=7)

        result = await db.execute(
            select(VerificationRequest).where(
                and_(
                    VerificationRequest.status == VerificationStatus.SENT,
                    VerificationRequest.contact_email.isnot(None),
                )
            )
        )
        requests = result.scalars().all()

        for req in requests:
            if not req.sent_at:
                continue

            try:
                days_since_sent = (now - req.sent_at).days

                if days_since_sent >= 3 and not req.reminder_1_sent:
                    verification_link = f"{settings.FRONTEND_URL}/verify-response/{req.token}"
                    await email_service.send_email(
                        to_email=req.contact_email,
                        subject=f"[Reminder] {req.email_subject}",
                        html_body=email_service._email_template(
                            title="Verification Reminder",
                            preheader="Friendly reminder about a pending verification",
                            content=f"""
                            <h2>Verification Reminder</h2>
                            <p>This is a friendly reminder about a pending verification request sent 3 days ago.</p>
                            <pre style="font-family:inherit;white-space:pre-wrap;">{req.email_body}</pre>
                            <p style="text-align:center;margin:32px 0;">
                                <a href="{verification_link}" class="btn">Complete Verification</a>
                            </p>
                            """,
                        ),
                    )
                    req.reminder_1_sent = True

                elif days_since_sent >= 7 and not req.reminder_2_sent:
                    verification_link = f"{settings.FRONTEND_URL}/verify-response/{req.token}"
                    await email_service.send_email(
                        to_email=req.contact_email,
                        subject=f"[Final Reminder] {req.email_subject}",
                        html_body=email_service._email_template(
                            title="Final Verification Reminder",
                            preheader="Final reminder about a pending verification",
                            content=f"""
                            <h2>Final Verification Reminder</h2>
                            <p>This is the final reminder for a verification request sent 7 days ago. No response will be recorded as unverified.</p>
                            <p style="text-align:center;margin:32px 0;">
                                <a href="{verification_link}" class="btn">Complete Verification</a>
                            </p>
                            """,
                        ),
                    )
                    req.reminder_2_sent = True

                    # Mark as expired if no response after 14 days
                    if days_since_sent >= 14:
                        req.status = VerificationStatus.EXPIRED

            except Exception as e:
                logger.error(f"Followup failed for request {req.id}: {e}")
                continue

        await db.commit()
        logger.info(f"Followup reminders processed for {len(requests)} requests")
