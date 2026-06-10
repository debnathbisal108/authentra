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


@celery_app.task(name="app.tasks.analysis_tasks.run_fraud_analysis", bind=True)
def run_fraud_analysis(self, candidate_id: str):
    return run_async(_fraud_analysis_async(candidate_id))


async def _fraud_analysis_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import Candidate, EmploymentRecord, EducationRecord, FraudFlag
    from app.services.fraud_detection import analyze_fraud
    from sqlalchemy import select, delete

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                return

            emp_result = await db.execute(
                select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id)
            )
            education_result = await db.execute(
                select(EducationRecord).where(EducationRecord.candidate_id == candidate_id)
            )

            emp_list = [
                {
                    "company_name": e.company_name,
                    "job_title": e.job_title,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "is_current": e.is_current,
                }
                for e in emp_result.scalars().all()
            ]
            edu_list = [
                {
                    "institution_name": e.institution_name,
                    "degree": e.degree,
                    "start_year": e.start_year,
                    "end_year": e.end_year,
                }
                for e in education_result.scalars().all()
            ]

            # Delete existing flags
            await db.execute(
                delete(FraudFlag).where(FraudFlag.candidate_id == candidate_id)
            )

            flags = analyze_fraud(emp_list, edu_list, candidate.raw_text or "")

            for flag in flags:
                ff = FraudFlag(
                    candidate_id=candidate_id,
                    flag_type=flag["flag_type"],
                    description=flag["description"],
                    severity=flag["severity"],
                    details=flag.get("details", {}),
                )
                db.add(ff)

            await db.commit()

            # Run risk scoring
            run_risk_scoring.delay(str(candidate_id))

        except Exception as e:
            logger.error(f"Fraud analysis failed for {candidate_id}: {e}")
            raise


@celery_app.task(name="app.tasks.analysis_tasks.run_risk_scoring", bind=True)
def run_risk_scoring(self, candidate_id: str):
    return run_async(_risk_scoring_async(candidate_id))


async def _risk_scoring_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord, FraudFlag,
        RiskScore, CandidateStatus, RiskLevel, FinalVerdict, VerificationStatus
    )
    from app.services.llm_service import llm_service, RISK_SCORING_SYSTEM, RISK_SCORING_PROMPT
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

            emp_result = await db.execute(
                select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id)
            )
            edu_result = await db.execute(
                select(EducationRecord).where(EducationRecord.candidate_id == candidate_id)
            )
            fraud_result = await db.execute(
                select(FraudFlag).where(FraudFlag.candidate_id == candidate_id)
            )

            emp_records = emp_result.scalars().all()
            edu_records = edu_result.scalars().all()
            fraud_flags = fraud_result.scalars().all()

            # Build verification data for LLM
            emp_verified = sum(1 for e in emp_records if e.verification_status == VerificationStatus.VERIFIED)
            emp_total = len(emp_records)
            edu_verified = sum(1 for e in edu_records if e.verification_status == VerificationStatus.VERIFIED)
            edu_total = len(edu_records)

            high_flags = [f for f in fraud_flags if f.severity in ("high", "critical")]
            medium_flags = [f for f in fraud_flags if f.severity == "medium"]
            low_flags = [f for f in fraud_flags if f.severity == "low"]

            verification_data = {
                "employment_verification": {
                    "total": emp_total,
                    "verified": emp_verified,
                    "verification_rate": (emp_verified / emp_total * 100) if emp_total else 0,
                },
                "education_verification": {
                    "total": edu_total,
                    "verified": edu_verified,
                },
                "fraud_flags": {
                    "total": len(fraud_flags),
                    "high_critical": len(high_flags),
                    "medium": len(medium_flags),
                    "low": len(low_flags),
                    "flags": [{"type": f.flag_type, "severity": f.severity, "description": f.description} for f in fraud_flags],
                },
            }

            prompt = RISK_SCORING_PROMPT.format(verification_data=json.dumps(verification_data, indent=2))

            try:
                score_data = await llm_service.complete_json(prompt, system=RISK_SCORING_SYSTEM)
            except Exception:
                # Compute deterministic score if LLM unavailable
                fraud_penalty = len(high_flags) * 20 + len(medium_flags) * 10 + len(low_flags) * 3
                emp_score = max(0, 50 - (emp_total - emp_verified) * 10) if emp_total else 50
                edu_score = max(0, 50 - (edu_total - edu_verified) * 10) if edu_total else 50
                fraud_score = min(100, fraud_penalty)
                total = min(100, (emp_score * 0.35 + edu_score * 0.25 + fraud_score * 0.40))
                score_data = {
                    "total_score": total,
                    "risk_level": "low" if total <= 25 else "moderate" if total <= 50 else "high" if total <= 75 else "critical",
                    "employment_score": emp_score,
                    "education_score": edu_score,
                    "fraud_score": fraud_score,
                    "public_check_score": 0,
                    "explanation": "Automated scoring based on verification results.",
                    "final_verdict": "clear" if total <= 25 else "review_required" if total <= 50 else "reject",
                    "ai_recommendation": "Please review candidate details manually.",
                }

            # Map strings to enums
            risk_level_map = {"low": RiskLevel.LOW, "moderate": RiskLevel.MODERATE, "high": RiskLevel.HIGH, "critical": RiskLevel.CRITICAL}
            verdict_map = {"clear": FinalVerdict.CLEAR, "review_required": FinalVerdict.REVIEW_REQUIRED, "reject": FinalVerdict.REJECT}

            # Get or create risk score record
            rs_result = await db.execute(
                select(RiskScore).where(RiskScore.candidate_id == candidate_id)
            )
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

            await db.flush()

            # Generate PDF report
            generate_report.delay(candidate_id)

        except Exception as e:
            logger.error(f"Risk scoring failed for {candidate_id}: {e}")
            raise


@celery_app.task(name="app.tasks.analysis_tasks.generate_report", bind=True)
def generate_report(self, candidate_id: str):
    return run_async(_generate_report_async(candidate_id))


async def _generate_report_async(candidate_id: str):
    from app.db.session import AsyncSessionLocal
    from app.models.models import (
        Candidate, EmploymentRecord, EducationRecord, FraudFlag,
        RiskScore, CandidateStatus, Organization, User, Notification
    )
    from app.services.report_generator import generate_verification_report
    from app.core.security import decrypt_field
    from app.services.email_service import email_service
    from sqlalchemy import select
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                return

            emp_result = await db.execute(
                select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id)
            )
            edu_result = await db.execute(
                select(EducationRecord).where(EducationRecord.candidate_id == candidate_id)
            )
            fraud_result = await db.execute(
                select(FraudFlag).where(FraudFlag.candidate_id == candidate_id)
            )
            rs_result = await db.execute(
                select(RiskScore).where(RiskScore.candidate_id == candidate_id)
            )
            org_result = await db.execute(
                select(Organization).where(Organization.id == candidate.organization_id)
            )

            emp_records = [
                {
                    "company_name": e.company_name,
                    "job_title": e.job_title,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "is_current": e.is_current,
                    "verification_status": e.verification_status.value if e.verification_status else "pending",
                }
                for e in emp_result.scalars().all()
            ]
            edu_records = [
                {
                    "institution_name": e.institution_name,
                    "degree": e.degree,
                    "field_of_study": e.field_of_study,
                    "start_year": e.start_year,
                    "end_year": e.end_year,
                    "verification_status": e.verification_status.value if e.verification_status else "pending",
                }
                for e in edu_result.scalars().all()
            ]
            fraud_flags = [
                {
                    "flag_type": f.flag_type,
                    "description": f.description,
                    "severity": f.severity.value if f.severity else "low",
                }
                for f in fraud_result.scalars().all()
            ]

            risk_score = rs_result.scalar_one_or_none()
            org = org_result.scalar_one_or_none()

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
                employment_records=emp_records,
                education_records=edu_records,
                fraud_flags=fraud_flags,
                risk_score=score_dict,
                organization_name=org.name if org else "Unknown Organization",
            )

            if risk_score:
                risk_score.report_data = pdf_bytes
                risk_score.report_generated = True
                risk_score.report_generated_at = datetime.utcnow()

            candidate.status = CandidateStatus.REPORT_READY
            await db.flush()

            # Notify recruiter
            user_result = await db.execute(
                select(User).where(User.id == candidate.created_by_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                notif = Notification(
                    user_id=user.id,
                    title="Verification Report Ready",
                    message=f"Background check for {candidate.full_name} is complete.",
                    notification_type="report_ready",
                    entity_type="candidate",
                    entity_id=candidate_id,
                )
                db.add(notif)

                # Send email notification
                await email_service.send_report_ready(
                    to_email=user.email,
                    user_name=user.full_name,
                    candidate_name=candidate.full_name or "Candidate",
                    candidate_id=candidate_id,
                )

            await db.commit()
            logger.info(f"Report generated for candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Report generation failed for {candidate_id}: {e}")
            raise
