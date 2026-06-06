import asyncio
import logging
from datetime import datetime
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.consent_tasks.send_consent_email", bind=True, max_retries=3)
def send_consent_email(self, candidate_id: str):
    return run_async(_send_consent_async(candidate_id))


async def _send_consent_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import Candidate, Consent, Organization
    from app.core.security import create_consent_token, decrypt_field
    from app.services.email_service import email_service
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                return

            candidate_email = decrypt_field(candidate.email_encrypted) if candidate.email_encrypted else None
            if not candidate_email:
                logger.warning(f"No email for candidate {candidate_id}")
                return

            org_result = await db.execute(
                select(Organization).where(Organization.id == candidate.organization_id)
            )
            org = org_result.scalar_one_or_none()

            # Create or get consent record
            consent_result = await db.execute(
                select(Consent).where(Consent.candidate_id == candidate_id)
            )
            consent = consent_result.scalar_one_or_none()

            if not consent:
                token = create_consent_token(candidate_id)
                consent = Consent(
                    candidate_id=candidate_id,
                    token=token,
                )
                db.add(consent)
                await db.flush()

            # Send email
            success = await email_service.send_consent_email(
                to_email=candidate_email,
                candidate_name=candidate.full_name or "Candidate",
                company_name=org.name if org else "Our Company",
                consent_token=consent.token,
            )

            if success:
                consent.email_sent_at = datetime.utcnow()
                await db.commit()
                logger.info(f"Consent email sent to candidate {candidate_id}")
            else:
                logger.error(f"Failed to send consent email to {candidate_email}")

        except Exception as e:
            logger.error(f"Error sending consent email for {candidate_id}: {e}")
            raise
