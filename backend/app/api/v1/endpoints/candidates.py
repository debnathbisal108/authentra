# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks
from app.tasks.pipeline import run_resume_pipeline

from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
import uuid
from datetime import datetime

from app.db.session import get_db
from app.models.models import (
    Candidate, Resume, EmploymentRecord, EducationRecord,
    FraudFlag, RiskScore, Consent, AuditLog, CandidateStatus
)
from app.schemas.schemas import (
    CandidateResponse, CandidateDetailResponse,
    EmploymentContactUpdate, EducationContactUpdate
)
from app.api.deps import get_current_user
from app.models.models import User
from app.core.security import decrypt_field
from app.core.config import settings

router = APIRouter()


@router.post("", status_code=201)
# async def upload_candidate(
#     request: Request,
#     resume: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
async def upload_candidate(
    request: Request,
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
        # Validate file type
    filename = resume.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx", "doc"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    # Read file
    file_data = await resume.read()
    max_size = settings.MAX_RESUME_SIZE_MB * 1024 * 1024
    if len(file_data) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {settings.MAX_RESUME_SIZE_MB}MB")

    # Create candidate
    candidate = Candidate(
        organization_id=current_user.organization_id,
        created_by_id=str(current_user.id),
        status=CandidateStatus.PENDING_CONSENT,
    )
    db.add(candidate)
    await db.flush()

    # Create resume record
    resume_record = Resume(
        candidate_id=str(candidate.id),
        filename=filename,
        file_type=ext,
        file_size=len(file_data),
        file_data=file_data,
        parse_status="pending",
    )
    db.add(resume_record)

    # Audit log
    log = AuditLog(
        user_id=str(current_user.id),
        organization_id=current_user.organization_id,
        action="candidate_created",
        entity_type="candidate",
        entity_id=str(candidate.id),
        ip_address=request.client.host if request.client else None,
    )
    db.add(log)
    await db.commit()

    # Trigger resume parsing task
    # try:
    #     from app.tasks.resume_tasks import parse_resume
    #     parse_resume.delay(str(candidate.id))
    # except Exception as e:
    #     import logging
    #     logging.getLogger(__name__).warning(f"Could not queue resume task: {e}")
    
    background_tasks.add_task(run_resume_pipeline, str(candidate.id))
    return {"id": str(candidate.id), "message": "Resume uploaded. Processing will begin shortly."}

@router.get("", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Candidate).where(
        Candidate.organization_id == current_user.organization_id
    ).order_by(Candidate.created_at.desc()).offset(skip).limit(limit)

    if status:
        try:
            status_enum = CandidateStatus(status)
            query = select(Candidate).where(
                and_(
                    Candidate.organization_id == current_user.organization_id,
                    Candidate.status == status_enum,
                )
            ).order_by(Candidate.created_at.desc()).offset(skip).limit(limit)
        except ValueError:
            pass

    result = await db.execute(query)
    candidates = result.scalars().all()

    return [_map_candidate(c) for c in candidates]


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

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
    consent_result = await db.execute(
        select(Consent).where(Consent.candidate_id == candidate_id)
    )

    base = _map_candidate(candidate)

    return {
        **base,
        "employment_records": [
            {
                "id": str(e.id),
                "company_name": e.company_name,
                "job_title": e.job_title,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "location": e.location,
                "contact_email": e.contact_email,
                "verification_status": e.verification_status.value if e.verification_status else "pending",
                "verified_title": e.verified_title,
                "verified_dates": e.verified_dates,
                "verifier_notes": e.verifier_notes,
            }
            for e in emp_result.scalars().all()
        ],
        "education_records": [
            {
                "id": str(e.id),
                "institution_name": e.institution_name,
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "start_year": e.start_year,
                "end_year": e.end_year,
                "contact_email": e.contact_email,
                "verification_status": e.verification_status.value if e.verification_status else "pending",
                "verifier_notes": e.verifier_notes,
            }
            for e in edu_result.scalars().all()
        ],
        "fraud_flags": [
            {
                "id": str(f.id),
                "flag_type": f.flag_type,
                "description": f.description,
                "severity": f.severity.value if f.severity else "low",
                "details": f.details or {},
                "created_at": f.created_at,
            }
            for f in fraud_result.scalars().all()
        ],
        "risk_score": _map_risk_score(rs_result.scalar_one_or_none()),
        "consent": _map_consent(consent_result.scalar_one_or_none()),
    }


@router.patch("/{candidate_id}/employment/{record_id}/contact")
async def update_employment_contact(
    candidate_id: str,
    record_id: str,
    payload: EmploymentContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmploymentRecord).where(
            and_(
                EmploymentRecord.id == record_id,
                EmploymentRecord.candidate_id == candidate_id,
            )
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Employment record not found")

    record.contact_email = payload.contact_email
    await db.commit()
    return {"message": "Contact updated"}


@router.patch("/{candidate_id}/education/{record_id}/contact")
async def update_education_contact(
    candidate_id: str,
    record_id: str,
    payload: EducationContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EducationRecord).where(
            and_(
                EducationRecord.id == record_id,
                EducationRecord.candidate_id == candidate_id,
            )
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Education record not found")

    record.contact_email = payload.contact_email
    await db.commit()
    return {"message": "Contact updated"}


@router.post("/{candidate_id}/send-verifications")
async def send_verifications(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger verification emails for a candidate."""
    result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if candidate.status not in (CandidateStatus.CONSENT_GRANTED, CandidateStatus.VERIFICATION_IN_PROGRESS):
        raise HTTPException(status_code=400, detail="Candidate has not granted consent yet")

    from app.tasks.verification_tasks import start_verifications
    start_verifications.delay(candidate_id)

    return {"message": "Verification emails will be sent shortly"}


@router.get("/{candidate_id}/report")
async def download_report(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    rs_result = await db.execute(
        select(RiskScore).where(RiskScore.candidate_id == candidate_id)
    )
    risk_score = rs_result.scalar_one_or_none()

    if not risk_score or not risk_score.report_data:
        raise HTTPException(status_code=404, detail="Report not ready yet")

    filename = f"authentra_report_{(candidate.full_name or 'candidate').replace(' ', '_')}.pdf"
    return Response(
        content=bytes(risk_score.report_data),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR erasure."""
    result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Anonymize PII
    candidate.full_name = "[DELETED]"
    candidate.email_encrypted = None
    candidate.phone_encrypted = None
    candidate.linkedin_url = None
    candidate.raw_text = None
    candidate.skills = []

    log = AuditLog(
        user_id=str(current_user.id),
        organization_id=current_user.organization_id,
        action="candidate_deleted",
        entity_type="candidate",
        entity_id=candidate_id,
        details={"gdpr_erasure": True},
    )
    db.add(log)
    await db.commit()
    return {"message": "Candidate data erased"}


@router.get("/{candidate_id}/export")
async def export_candidate_data(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR data export."""
    result = await db.execute(
        select(Candidate).where(
            and_(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    emp_result = await db.execute(
        select(EmploymentRecord).where(EmploymentRecord.candidate_id == candidate_id)
    )
    edu_result = await db.execute(
        select(EducationRecord).where(EducationRecord.candidate_id == candidate_id)
    )

    return {
        "candidate_id": candidate_id,
        "exported_at": datetime.utcnow(),
        "data": {
            "full_name": candidate.full_name,
            "email": decrypt_field(candidate.email_encrypted) if candidate.email_encrypted else None,
            "phone": decrypt_field(candidate.phone_encrypted) if candidate.phone_encrypted else None,
            "linkedin": candidate.linkedin_url,
            "skills": candidate.skills,
            "employment": [
                {
                    "company": e.company_name,
                    "title": e.job_title,
                    "start": e.start_date,
                    "end": e.end_date,
                }
                for e in emp_result.scalars().all()
            ],
            "education": [
                {
                    "institution": e.institution_name,
                    "degree": e.degree,
                    "years": f"{e.start_year}-{e.end_year}",
                }
                for e in edu_result.scalars().all()
            ],
        },
    }


def _map_candidate(c: Candidate) -> dict:
    return {
        "id": str(c.id),
        "full_name": c.full_name,
        "email": decrypt_field(c.email_encrypted) if c.email_encrypted else None,
        "phone": decrypt_field(c.phone_encrypted) if c.phone_encrypted else None,
        "linkedin_url": c.linkedin_url,
        "skills": c.skills or [],
        "status": c.status.value if c.status else "pending_consent",
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _map_risk_score(rs):
    if not rs:
        return None
    return {
        "id": str(rs.id),
        "total_score": rs.total_score,
        "risk_level": rs.risk_level.value if rs.risk_level else "low",
        "employment_score": rs.employment_score,
        "education_score": rs.education_score,
        "fraud_score": rs.fraud_score,
        "public_check_score": rs.public_check_score,
        "explanation": rs.explanation,
        "final_verdict": rs.final_verdict.value if rs.final_verdict else None,
        "ai_recommendation": rs.ai_recommendation,
        "report_generated": rs.report_generated,
        "report_generated_at": rs.report_generated_at,
    }


def _map_consent(c):
    if not c:
        return None
    return {
        "id": str(c.id),
        "granted": c.granted,
        "declined": c.declined,
        "granted_at": c.granted_at,
        "consent_version": c.consent_version,
        "email_sent_at": c.email_sent_at,
    }
