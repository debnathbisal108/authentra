import asyncio
import uuid
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


@celery_app.task(name="app.tasks.verification_tasks.start_verifications", bind=True)
def start_verifications(self, candidate_id: str):
    return run_async(_start_verifications_async(candidate_id))


async def _start_verifications_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord,
        VerificationRequest, CandidateStatus, VerificationStatus
    )
    from app.services.llm_service import llm_service, VERIFICATION_EMAIL_PROMPT
    from app.core.config import settings
    from app.services.email_service import email_service
    from sqlalchemy import select
    import json

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                return

            candidate.status = CandidateStatus.VERIFICATION_IN_PROGRESS
            await db.flush()

            # Get employment records
            emp_result = await db.execute(
                select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id)
            )
            employment_records = emp_result.scalars().all()

            # Get education records
            edu_result = await db.execute(
                select(EducationRecord).where(EducationRecord.candidate_id == candidate_id)
            )
            education_records = edu_result.scalars().all()

            # Create verification requests for employment
            for emp in employment_records:
                if not emp.contact_email:
                    continue

                token = str(uuid.uuid4())
                verification_link = f"{settings.FRONTEND_URL}/verify-response/{token}"

                # Generate email via LLM
                prompt = VERIFICATION_EMAIL_PROMPT.format(
                    candidate_name=candidate.full_name or "the candidate",
                    company_name=emp.company_name,
                    job_title=emp.job_title or "unknown position",
                    dates=f"{emp.start_date or '?'} to {emp.end_date or 'present'}",
                    verification_link=verification_link,
                )
                try:
                    result_json = await llm_service.complete_json(prompt)
                    subject = result_json.get("subject", f"Employment Verification: {candidate.full_name}")
                    body = result_json.get("body", f"Please verify employment for {candidate.full_name} at {emp.company_name}.")
                except Exception:
                    subject = f"Employment Verification Request - {candidate.full_name}"
                    body = (
                        f"Dear HR Team,\n\n"
                        f"We are conducting a background verification for {candidate.full_name}, "
                        f"who has listed {emp.company_name} as a previous employer "
                        f"({emp.job_title or 'unknown position'}, {emp.start_date or '?'} to {emp.end_date or 'present'}).\n\n"
                        f"Please click the link below to complete the verification form:\n{verification_link}\n\n"
                        f"Thank you for your assistance.\n\nAuthentra AI Verification Team"
                    )

                vr = VerificationRequest(
                    candidate_id=candidate_id,
                    employment_record_id=emp.id,
                    verification_type="employment",
                    contact_email=emp.contact_email,
                    email_subject=subject,
                    email_body=body,
                    token=token,
                    status=VerificationStatus.PENDING,
                )
                db.add(vr)
                await db.flush()

                # Send email
                sent = await email_service.send_verification_request(
                    to_email=emp.contact_email,
                    verification_type="employment",
                    candidate_name=candidate.full_name or "Candidate",
                    entity_name=emp.company_name,
                    verification_link=verification_link,
                    email_body=body,
                )
                if sent:
                    vr.status = VerificationStatus.SENT
                    vr.sent_at = datetime.utcnow()
                    emp.verification_status = VerificationStatus.SENT

            # Create verification requests for education
            for edu in education_records:
                if not edu.contact_email:
                    continue

                token = str(uuid.uuid4())
                verification_link = f"{settings.FRONTEND_URL}/verify-response/{token}"

                vr = VerificationRequest(
                    candidate_id=candidate_id,
                    education_record_id=edu.id,
                    verification_type="education",
                    contact_email=edu.contact_email,
                    email_subject=f"Education Verification Request - {candidate.full_name}",
                    email_body=(
                        f"Dear Registrar,\n\n"
                        f"We are verifying that {candidate.full_name} attended {edu.institution_name} "
                        f"({edu.degree or 'unknown degree'}, {edu.start_year or '?'} to {edu.end_year or '?'}).\n\n"
                        f"Please complete the verification form: {verification_link}\n\n"
                        f"Thank you.\nAuthentra AI"
                    ),
                    token=token,
                    status=VerificationStatus.PENDING,
                )
                db.add(vr)
                await db.flush()

                sent = await email_service.send_verification_request(
                    to_email=edu.contact_email,
                    verification_type="education",
                    candidate_name=candidate.full_name or "Candidate",
                    entity_name=edu.institution_name,
                    verification_link=verification_link,
                    email_body=vr.email_body,
                )
                if sent:
                    vr.status = VerificationStatus.SENT
                    vr.sent_at = datetime.utcnow()
                    edu.verification_status = VerificationStatus.SENT

            await db.commit()

            # Trigger fraud and risk analysis
            from app.tasks.analysis_tasks import run_fraud_analysis
            run_fraud_analysis.delay(str(candidate_id))

            logger.info(f"Verifications started for candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Error starting verifications for {candidate_id}: {e}")
            raise
