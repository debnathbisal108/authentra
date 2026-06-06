import asyncio
import json
import logging
from app.tasks.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.resume_tasks.parse_resume", bind=True, max_retries=3)
def parse_resume(self, candidate_id: str):
    """Parse resume and extract candidate information."""
    return run_async(_parse_resume_async(candidate_id))


async def _parse_resume_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import Candidate, Resume, EmploymentRecord, EducationRecord
    from app.services.resume_parser import extract_text
    from app.services.llm_service import llm_service, RESUME_PARSE_SYSTEM, RESUME_PARSE_PROMPT
    from app.core.security import decrypt_field
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                logger.error(f"Candidate {candidate_id} not found")
                return

            resume_result = await db.execute(
                select(Resume).where(Resume.candidate_id == candidate_id)
            )
            resume = resume_result.scalar_one_or_none()
            if not resume:
                logger.error(f"Resume for candidate {candidate_id} not found")
                return

            # Extract text
            text, error = extract_text(resume.file_data, resume.file_type)
            if error:
                resume.parse_status = "failed"
                resume.parse_error = error
                await db.commit()
                return

            resume.extracted_text = text
            candidate.raw_text = text

            # Parse with LLM
            prompt = RESUME_PARSE_PROMPT.format(resume_text=text[:8000])
            parsed = await llm_service.complete_json(prompt, system=RESUME_PARSE_SYSTEM)

            # Update candidate
            candidate.full_name = parsed.get("full_name") or candidate.full_name
            
            if parsed.get("email"):
                from app.core.security import encrypt_field
                candidate.email_encrypted = encrypt_field(parsed["email"])
            
            if parsed.get("phone"):
                from app.core.security import encrypt_field
                candidate.phone_encrypted = encrypt_field(parsed["phone"])
            
            candidate.linkedin_url = parsed.get("linkedin") or candidate.linkedin_url
            candidate.skills = parsed.get("skills", [])

            # Create employment records
            for emp in parsed.get("employment", []):
                if not emp.get("company_name"):
                    continue
                record = EmploymentRecord(
                    candidate_id=candidate_id,
                    company_name=emp.get("company_name", ""),
                    job_title=emp.get("job_title"),
                    start_date=emp.get("start_date"),
                    end_date=emp.get("end_date"),
                    is_current=emp.get("is_current", False),
                    location=emp.get("location"),
                    description=emp.get("description"),
                )
                db.add(record)

            # Create education records
            for edu in parsed.get("education", []):
                if not edu.get("institution_name"):
                    continue
                record = EducationRecord(
                    candidate_id=candidate_id,
                    institution_name=edu.get("institution_name", ""),
                    degree=edu.get("degree"),
                    field_of_study=edu.get("field_of_study"),
                    start_year=edu.get("start_year"),
                    end_year=edu.get("end_year"),
                    gpa=edu.get("gpa"),
                )
                db.add(record)

            resume.parse_status = "completed"
            await db.commit()

            # Trigger consent email
            from app.tasks.consent_tasks import send_consent_email
            send_consent_email.delay(candidate_id)

            logger.info(f"Resume parsed for candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Error parsing resume for candidate {candidate_id}: {e}")
            if resume:
                resume.parse_status = "failed"
                resume.parse_error = str(e)
                await db.commit()
            raise
