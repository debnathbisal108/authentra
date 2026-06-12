import asyncio
import logging
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


# async def run_resume_pipeline(candidate_id: str):
#     """Parse resume then send consent email."""
#     try:
#         await _parse_resume(candidate_id)
#         await _send_consent_email(candidate_id)
#     except Exception as e:
#         logger.error(f"Resume pipeline failed for {candidate_id}: {e}", exc_info=True)

async def run_resume_pipeline(candidate_id: str):
    """Parse resume then immediately run full analysis (consent skipped)."""
    try:
        await _parse_resume(candidate_id)
        await _set_status_consent_granted(candidate_id)
        await _run_fraud_analysis(candidate_id)
        await _run_risk_scoring(candidate_id)
        await _generate_report(candidate_id)
    except Exception as e:
        logger.error(f"Resume pipeline failed for {candidate_id}: {e}", exc_info=True)

async def run_verification_pipeline(candidate_id: str):
    """Send verification emails then run analysis."""
    try:
        await _start_verifications(candidate_id)
        await _run_fraud_analysis(candidate_id)
        await _run_risk_scoring(candidate_id)
        await _generate_report(candidate_id)
    except Exception as e:
        logger.error(f"Verification pipeline failed for {candidate_id}: {e}", exc_info=True)


async def run_analysis_pipeline(candidate_id: str):
    """Re-run fraud + risk + report after a verification response."""
    try:
        await _run_fraud_analysis(candidate_id)
        await _run_risk_scoring(candidate_id)
        await _generate_report(candidate_id)
    except Exception as e:
        logger.error(f"Analysis pipeline failed for {candidate_id}: {e}", exc_info=True)


# ─── Step implementations ──────────────────────────────────────────────────────

async def _parse_resume(candidate_id: str):
    from sqlalchemy import select
    from app.models.models import Candidate, Resume, EmploymentRecord, EducationRecord
    from app.services.resume_parser import extract_text
    from app.services.llm_service import llm_service, RESUME_PARSE_SYSTEM, RESUME_PARSE_PROMPT
    from app.core.security import encrypt_field

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        resume_result = await db.execute(select(Resume).where(Resume.candidate_id == candidate_id))
        resume = resume_result.scalar_one_or_none()
        if not resume:
            return

        text, error = extract_text(resume.file_data, resume.file_type)
        if error:
            resume.parse_status = "failed"
            resume.parse_error = error
            await db.commit()
            return

        resume.extracted_text = text
        candidate.raw_text = text

        prompt = RESUME_PARSE_PROMPT.format(resume_text=text[:8000])
        parsed = await llm_service.complete_json(prompt, system=RESUME_PARSE_SYSTEM)

        candidate.full_name = parsed.get("full_name") or candidate.full_name
        if parsed.get("email"):
            candidate.email_encrypted = encrypt_field(parsed["email"])
        if parsed.get("phone"):
            candidate.phone_encrypted = encrypt_field(parsed["phone"])
        candidate.linkedin_url = parsed.get("linkedin") or candidate.linkedin_url
        candidate.skills = parsed.get("skills", [])

        for emp in parsed.get("employment", []):
            if not emp.get("company_name"):
                continue
            db.add(EmploymentRecord(
                candidate_id=candidate_id,
                company_name=emp.get("company_name", ""),
                job_title=emp.get("job_title"),
                start_date=emp.get("start_date"),
                end_date=emp.get("end_date"),
                is_current=emp.get("is_current", False),
                location=emp.get("location"),
                description=emp.get("description"),
            ))

        for edu in parsed.get("education", []):
            if not edu.get("institution_name"):
                continue
            db.add(EducationRecord(
                candidate_id=candidate_id,
                institution_name=edu.get("institution_name", ""),
                degree=edu.get("degree"),
                field_of_study=edu.get("field_of_study"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
                gpa=edu.get("gpa"),
            ))

        resume.parse_status = "completed"
        await db.commit()
        logger.info(f"Resume parsed for candidate {candidate_id}")


async def _send_consent_email(candidate_id: str):
    from sqlalchemy import select
    from datetime import datetime
    from app.models.models import Candidate, Consent, Organization
    from app.core.security import create_consent_token, decrypt_field
    from app.services.email_service import email_service

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        candidate_email = decrypt_field(candidate.email_encrypted) if candidate.email_encrypted else None
        if not candidate_email:
            logger.warning(f"No email for candidate {candidate_id}, skipping consent email")
            return

        org_result = await db.execute(select(Organization).where(Organization.id == candidate.organization_id))
        org = org_result.scalar_one_or_none()

        consent_result = await db.execute(select(Consent).where(Consent.candidate_id == candidate_id))
        consent = consent_result.scalar_one_or_none()

        if not consent:
            token = create_consent_token(candidate_id)
            consent = Consent(candidate_id=candidate_id, token=token)
            db.add(consent)
            await db.flush()

        success = await email_service.send_consent_email(
            to_email=candidate_email,
            candidate_name=candidate.full_name or "Candidate",
            company_name=org.name if org else "Our Company",
            consent_token=consent.token,
        )

        if success:
            consent.email_sent_at = datetime.utcnow()
            await db.commit()

async def _set_status_consent_granted(candidate_id: str):
    """Skip consent flow — mark candidate as consent granted immediately."""
    from sqlalchemy import select
    from app.models.models import Candidate, CandidateStatus

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if candidate:
            candidate.status = CandidateStatus.CONSENT_GRANTED
            await db.commit()

async def _start_verifications(candidate_id: str):
    import uuid as uuid_lib
    from datetime import datetime
    from sqlalchemy import select
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord,
        VerificationRequest, VerificationStatus, CandidateStatus
    )
    from app.services.llm_service import llm_service, VERIFICATION_EMAIL_PROMPT
    from app.services.email_service import email_service
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        candidate.status = CandidateStatus.VERIFICATION_IN_PROGRESS

        emp_result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id))
        edu_result = await db.execute(select(EducationRecord).where(EducationRecord.candidate_id == candidate_id))

        for emp in emp_result.scalars().all():
            if not emp.contact_email:
                continue
            token = str(uuid_lib.uuid4())
            verification_link = f"{settings.FRONTEND_URL}/verify-response/{token}"

            try:
                result_json = await llm_service.complete_json(
                    VERIFICATION_EMAIL_PROMPT.format(
                        candidate_name=candidate.full_name or "the candidate",
                        company_name=emp.company_name,
                        job_title=emp.job_title or "unknown position",
                        dates=f"{emp.start_date or '?'} to {emp.end_date or 'present'}",
                        verification_link=verification_link,
                    )
                )
                subject = result_json.get("subject", f"Employment Verification: {candidate.full_name}")
                body = result_json.get("body", "")
            except Exception:
                subject = f"Employment Verification Request - {candidate.full_name}"
                body = (
                    f"Dear HR Team,\n\nWe are verifying employment for {candidate.full_name} "
                    f"at {emp.company_name} ({emp.job_title}, {emp.start_date} to {emp.end_date or 'present'}).\n\n"
                    f"Please complete verification: {verification_link}\n\nAuthentra AI"
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

        for edu in edu_result.scalars().all():
            if not edu.contact_email:
                continue
            token = str(uuid_lib.uuid4())
            verification_link = f"{settings.FRONTEND_URL}/verify-response/{token}"
            body = (
                f"Dear Registrar,\n\nWe are verifying that {candidate.full_name} attended "
                f"{edu.institution_name} ({edu.degree}, {edu.start_year} to {edu.end_year}).\n\n"
                f"Please complete verification: {verification_link}\n\nAuthentra AI"
            )
            vr = VerificationRequest(
                candidate_id=candidate_id,
                education_record_id=edu.id,
                verification_type="education",
                contact_email=edu.contact_email,
                email_subject=f"Education Verification - {candidate.full_name}",
                email_body=body,
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
                email_body=body,
            )
            if sent:
                vr.status = VerificationStatus.SENT
                vr.sent_at = datetime.utcnow()
                edu.verification_status = VerificationStatus.SENT

        await db.commit()


async def _run_fraud_analysis(candidate_id: str):
    from sqlalchemy import select, delete
    from app.models.models import Candidate, EmploymentRecord, EducationRecord, FraudFlag
    from app.services.fraud_detection import analyze_fraud

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        emp_result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id))
        edu_result = await db.execute(select(EducationRecord).where(EducationRecord.candidate_id == candidate_id))

        emp_list = [{"company_name": e.company_name, "job_title": e.job_title, "start_date": e.start_date, "end_date": e.end_date, "is_current": e.is_current} for e in emp_result.scalars().all()]
        edu_list = [{"institution_name": e.institution_name, "degree": e.degree, "start_year": e.start_year, "end_year": e.end_year} for e in edu_result.scalars().all()]

        await db.execute(delete(FraudFlag).where(FraudFlag.candidate_id == candidate_id))

        for flag in analyze_fraud(emp_list, edu_list, candidate.raw_text or ""):
            db.add(FraudFlag(
                candidate_id=candidate_id,
                flag_type=flag["flag_type"],
                description=flag["description"],
                severity=flag["severity"],
                details=flag.get("details", {}),
            ))

        await db.commit()


async def _run_risk_scoring(candidate_id: str):
    import json
    from sqlalchemy import select
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord, FraudFlag,
        RiskScore, CandidateStatus, RiskLevel, FinalVerdict, VerificationStatus
    )
    from app.services.llm_service import llm_service, RISK_SCORING_SYSTEM, RISK_SCORING_PROMPT

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        emp_result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id))
        edu_result = await db.execute(select(EducationRecord).where(EducationRecord.candidate_id == candidate_id))
        fraud_result = await db.execute(select(FraudFlag).where(FraudFlag.candidate_id == candidate_id))

        emp_records = emp_result.scalars().all()
        edu_records = edu_result.scalars().all()
        fraud_flags = fraud_result.scalars().all()

        emp_verified = sum(1 for e in emp_records if e.verification_status == VerificationStatus.VERIFIED)
        high_flags = [f for f in fraud_flags if f.severity in ("high", "critical")]
        medium_flags = [f for f in fraud_flags if f.severity == "medium"]
        low_flags = [f for f in fraud_flags if f.severity == "low"]

        verification_data = {
            "employment_verification": {"total": len(emp_records), "verified": emp_verified},
            "education_verification": {"total": len(edu_records)},
            "fraud_flags": {
                "total": len(fraud_flags), "high_critical": len(high_flags),
                "medium": len(medium_flags), "low": len(low_flags),
                "flags": [{"type": f.flag_type, "severity": f.severity, "description": f.description} for f in fraud_flags],
            },
        }

        try:
            score_data = await llm_service.complete_json(
                RISK_SCORING_PROMPT.format(verification_data=json.dumps(verification_data, indent=2)),
                system=RISK_SCORING_SYSTEM
            )
        except Exception:
            fraud_penalty = len(high_flags) * 20 + len(medium_flags) * 10 + len(low_flags) * 3
            fraud_score = min(100, fraud_penalty)
            total = min(100, fraud_score)
            score_data = {
                "total_score": total, "risk_level": "low" if total <= 25 else "moderate" if total <= 50 else "high",
                "employment_score": 0, "education_score": 0, "fraud_score": fraud_score, "public_check_score": 0,
                "explanation": "Automated scoring.", "final_verdict": "clear" if total <= 25 else "review_required",
                "ai_recommendation": "Please review manually.",
            }

        risk_level_map = {"low": RiskLevel.LOW, "moderate": RiskLevel.MODERATE, "high": RiskLevel.HIGH, "critical": RiskLevel.CRITICAL}
        verdict_map = {"clear": FinalVerdict.CLEAR, "review_required": FinalVerdict.REVIEW_REQUIRED, "reject": FinalVerdict.REJECT}

        rs_result = await db.execute(select(RiskScore).where(RiskScore.candidate_id == candidate_id))
        risk_score = rs_result.scalar_one_or_none()
        if not risk_score:
            risk_score = RiskScore(candidate_id=candidate_id)
            db.add(risk_score)

        risk_score.total_score = float(score_data.get("total_score", 0))
        risk_score.risk_level = risk_level_map.get(score_data.get("risk_level", "low"), RiskLevel.LOW)
        risk_score.employment_score = float(score_data.get("employment_score", 0))
        risk_score.education_score = float(score_data.get("education_score", 0))
        risk_score.fraud_score = float(score_data.get("fraud_score", 0))
        risk_score.public_check_score = float(score_data.get("public_check_score", 0))
        risk_score.explanation = score_data.get("explanation", "")
        risk_score.final_verdict = verdict_map.get(score_data.get("final_verdict", "review_required"), FinalVerdict.REVIEW_REQUIRED)
        risk_score.ai_recommendation = score_data.get("ai_recommendation", "")
        await db.commit()


async def _generate_report(candidate_id: str):
    from datetime import datetime
    from sqlalchemy import select
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord, FraudFlag,
        RiskScore, CandidateStatus, Organization, User, Notification
    )
    from app.services.report_generator import generate_verification_report
    from app.services.email_service import email_service
    from app.core.security import decrypt_field

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return

        emp_result = await db.execute(select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id))
        edu_result = await db.execute(select(EducationRecord).where(EducationRecord.candidate_id == candidate_id))
        fraud_result = await db.execute(select(FraudFlag).where(FraudFlag.candidate_id == candidate_id))
        rs_result = await db.execute(select(RiskScore).where(RiskScore.candidate_id == candidate_id))
        org_result = await db.execute(select(Organization).where(Organization.id == candidate.organization_id))
        user_result = await db.execute(select(User).where(User.id == candidate.created_by_id))

        risk_score = rs_result.scalar_one_or_none()
        org = org_result.scalar_one_or_none()
        user = user_result.scalar_one_or_none()

        emp_list = [{"company_name": e.company_name, "job_title": e.job_title, "start_date": e.start_date, "end_date": e.end_date, "is_current": e.is_current, "verification_status": e.verification_status.value if e.verification_status else "pending"} for e in emp_result.scalars().all()]
        edu_list = [{"institution_name": e.institution_name, "degree": e.degree, "field_of_study": e.field_of_study, "start_year": e.start_year, "end_year": e.end_year, "verification_status": e.verification_status.value if e.verification_status else "pending"} for e in edu_result.scalars().all()]
        fraud_list = [{"flag_type": f.flag_type, "description": f.description, "severity": f.severity.value if f.severity else "low"} for f in fraud_result.scalars().all()]

        score_dict = {}
        if risk_score:
            score_dict = {
                "total_score": risk_score.total_score,
                "risk_level": risk_score.risk_level.value if risk_score.risk_level else "low",
                "employment_score": risk_score.employment_score,
                "education_score": risk_score.education_score,
                "fraud_score": risk_score.fraud_score,
                "public_check_score": risk_score.public_check_score,
                "explanation": risk_score.explanation,
                "final_verdict": risk_score.final_verdict.value if risk_score.final_verdict else None,
                "ai_recommendation": risk_score.ai_recommendation,
            }

        candidate_dict = {
            "full_name": candidate.full_name,
            "email": decrypt_field(candidate.email_encrypted) if candidate.email_encrypted else None,
            "phone": decrypt_field(candidate.phone_encrypted) if candidate.phone_encrypted else None,
            "linkedin_url": candidate.linkedin_url,
            "skills": candidate.skills or [],
        }

        pdf_bytes = generate_verification_report(
            candidate=candidate_dict,
            employment_records=emp_list,
            education_records=edu_list,
            fraud_flags=fraud_list,
            risk_score=score_dict,
            organization_name=org.name if org else "Unknown",
        )

        if risk_score:
            risk_score.report_data = pdf_bytes
            risk_score.report_generated = True
            risk_score.report_generated_at = datetime.utcnow()

        candidate.status = CandidateStatus.REPORT_READY

        if user:
            db.add(Notification(
                user_id=str(user.id),
                title="Verification Report Ready",
                message=f"Background check for {candidate.full_name} is complete.",
                notification_type="report_ready",
                entity_type="candidate",
                entity_id=str(candidate_id),
            ))
            await email_service.send_report_ready(
                to_email=user.email,
                user_name=user.full_name,
                candidate_name=candidate.full_name or "Candidate",
                candidate_id=str(candidate_id),
            )

        await db.commit()
        logger.info(f"Report generated for candidate {candidate_id}")
