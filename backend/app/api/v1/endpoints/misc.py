from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime

from app.db.session import get_db
from app.models.models import (
    Candidate, CandidateStatus, RiskScore, RiskLevel,
    Consent, VerificationRequest, VerificationResponse,
    VerificationStatus, User, Notification, AuditLog, SystemSettings
)
from app.api.deps import get_current_user
from app.core.security import verify_consent_token
from app.schemas.schemas import VerificationResponseSubmit, SettingsUpdate

router = APIRouter()


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id

    total = await db.scalar(
        select(func.count()).select_from(Candidate).where(Candidate.organization_id == org_id)
    )
    pending_consents = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            and_(Candidate.organization_id == org_id,
                 Candidate.status == CandidateStatus.PENDING_CONSENT)
        )
    )
    active = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            and_(Candidate.organization_id == org_id,
                 Candidate.status == CandidateStatus.VERIFICATION_IN_PROGRESS)
        )
    )
    completed = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            and_(Candidate.organization_id == org_id,
                 Candidate.status == CandidateStatus.REPORT_READY)
        )
    )

    # High risk candidates (score > 50)
    high_risk_ids = await db.execute(
        select(RiskScore.candidate_id).join(
            Candidate, Candidate.id == RiskScore.candidate_id
        ).where(
            and_(
                Candidate.organization_id == org_id,
                RiskScore.total_score > 50,
            )
        )
    )
    high_risk = len(high_risk_ids.scalars().all())

    # Status distribution
    status_data = {}
    for s in CandidateStatus:
        count = await db.scalar(
            select(func.count()).select_from(Candidate).where(
                and_(Candidate.organization_id == org_id, Candidate.status == s)
            )
        )
        status_data[s.value] = count or 0

    # Risk distribution
    risk_data = {}
    for level in RiskLevel:
        count = await db.scalar(
            select(func.count()).select_from(RiskScore).join(
                Candidate, Candidate.id == RiskScore.candidate_id
            ).where(
                and_(
                    Candidate.organization_id == org_id,
                    RiskScore.risk_level == level,
                )
            )
        )
        risk_data[level.value] = count or 0

    return {
        "stats": {
            "total_candidates": total or 0,
            "pending_consents": pending_consents or 0,
            "active_verifications": active or 0,
            "completed_verifications": completed or 0,
            "high_risk_candidates": high_risk,
        },
        "charts": {
            "verification_status": status_data,
            "risk_distribution": risk_data,
        },
    }


@router.get("/dashboard/activity")
async def get_recent_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id
        ).order_by(AuditLog.created_at.desc()).limit(20)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "created_at": l.created_at,
        }
        for l in logs
    ]


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id
        ).order_by(Notification.created_at.desc()).limit(50)
    )
    notifs = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "is_read": n.is_read,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "created_at": n.created_at,
        }
        for n in notifs
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == current_user.id)
        )
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
        await db.commit()
    return {"message": "Marked as read"}


# ─── Consent ──────────────────────────────────────────────────────────────────

@router.get("/consent/{token}")
async def get_consent_info(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint - get consent info for a token."""
    candidate_id = verify_consent_token(token)
    if not candidate_id:
        raise HTTPException(status_code=400, detail="Invalid or expired consent link")

    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Not found")

    from app.models.models import Organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == candidate.organization_id)
    )
    org = org_result.scalar_one_or_none()

    consent_result = await db.execute(
        select(Consent).where(Consent.token == token)
    )
    consent = consent_result.scalar_one_or_none()

    return {
        "candidate_name": candidate.full_name,
        "organization_name": org.name if org else "Unknown",
        "already_responded": consent.granted or consent.declined if consent else False,
        "granted": consent.granted if consent else False,
    }


@router.post("/consent/{token}/respond")
async def respond_to_consent(
    token: str,
    action: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint - accept or decline consent."""
    if action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'decline'")

    candidate_id = verify_consent_token(token)
    if not candidate_id:
        raise HTTPException(status_code=400, detail="Invalid or expired consent link")

    consent_result = await db.execute(
        select(Consent).where(Consent.token == token)
    )
    consent = consent_result.scalar_one_or_none()

    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")

    if consent.granted or consent.declined:
        return {"message": "Already responded"}

    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()

    if action == "accept":
        consent.granted = True
        consent.granted_at = datetime.utcnow()
        consent.ip_address = request.client.host if request.client else None
        consent.user_agent = request.headers.get("user-agent")
        candidate.status = CandidateStatus.CONSENT_GRANTED

        await db.commit()

        # Trigger verifications
        from app.tasks.verification_tasks import start_verifications
        start_verifications.delay(str(candidate_id))

        return {"message": "Consent granted. Verification process will begin shortly."}
    else:
        consent.declined = True
        candidate.status = CandidateStatus.CONSENT_DECLINED
        await db.commit()
        return {"message": "You have declined the verification. No further action will be taken."}


# ─── Verification Response (Public) ───────────────────────────────────────────

@router.get("/verify-response/{token}")
async def get_verification_form(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint - get verification form data."""
    result = await db.execute(
        select(VerificationRequest).where(VerificationRequest.token == token)
    )
    vr = result.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")

    if vr.status == VerificationStatus.REPLIED:
        return {"already_responded": True}

    # Mark as opened
    if vr.status == VerificationStatus.SENT:
        vr.status = VerificationStatus.OPENED
        vr.opened_at = datetime.utcnow()
        await db.commit()

    # Get candidate info
    cand_result = await db.execute(
        select(Candidate).where(Candidate.id == vr.candidate_id)
    )
    cand = cand_result.scalar_one_or_none()

    from app.models.models import EmploymentRecord
    entity_name = ""
    if vr.employment_record_id:
        emp_result = await db.execute(
            select(EmploymentRecord).where(EmploymentRecord.id == vr.employment_record_id)
        )
        emp = emp_result.scalar_one_or_none()
        if emp:
            entity_name = emp.company_name

    return {
        "already_responded": False,
        "verification_type": vr.verification_type,
        "candidate_name": cand.full_name if cand else "Unknown",
        "entity_name": entity_name,
        "email_body": vr.email_body,
    }


@router.post("/verify-response/{token}")
async def submit_verification_response(
    token: str,
    payload: VerificationResponseSubmit,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint - submit verification response."""
    result = await db.execute(
        select(VerificationRequest).where(VerificationRequest.token == token)
    )
    vr = result.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")

    if vr.status == VerificationStatus.REPLIED:
        return {"message": "Already responded. Thank you."}

    response = VerificationResponse(
        request_id=vr.id,
        responder_name=payload.responder_name,
        responder_email=str(payload.responder_email),
        responder_title=payload.responder_title,
        employed_confirmed=payload.employed_confirmed,
        job_title_confirmed=payload.job_title_confirmed,
        dates_confirmed=payload.dates_confirmed,
        additional_notes=payload.additional_notes,
        ip_address=request.client.host if request.client else None,
    )
    db.add(response)

    vr.status = VerificationStatus.REPLIED
    vr.replied_at = datetime.utcnow()
    vr.response_text = payload.additional_notes

    # Update employment/education record
    if vr.employment_record_id:
        emp_result = await db.execute(
            select(EmploymentRecord).where(EmploymentRecord.id == vr.employment_record_id)
        )
        emp = emp_result.scalar_one_or_none()
        if emp:
            emp.verification_status = VerificationStatus.VERIFIED if payload.employed_confirmed else VerificationStatus.FAILED
            emp.verified_title = payload.job_title_confirmed
            emp.verified_dates = payload.dates_confirmed
            emp.verifier_notes = payload.additional_notes

    await db.commit()

    # Re-run analysis with updated data
    from app.tasks.analysis_tasks import run_fraud_analysis
    run_fraud_analysis.delay(str(vr.candidate_id))

    return {"message": "Thank you for your response. It has been recorded."}


# ─── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SystemSettings).where(
            SystemSettings.organization_id == current_user.organization_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        return {}
    return {
        "smtp_host": s.smtp_host,
        "smtp_port": s.smtp_port,
        "smtp_user": s.smtp_user,
        "smtp_tls": s.smtp_tls,
        "consent_version": s.consent_version,
        "retention_days": s.retention_days,
        "auto_verify": s.auto_verify,
        "llm_provider": s.llm_provider,
    }


@router.patch("/settings")
async def update_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SystemSettings).where(
            SystemSettings.organization_id == current_user.organization_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        s = SystemSettings(organization_id=current_user.organization_id)
        db.add(s)

    if payload.smtp_host is not None:
        s.smtp_host = payload.smtp_host
    if payload.smtp_port is not None:
        s.smtp_port = payload.smtp_port
    if payload.smtp_user is not None:
        s.smtp_user = payload.smtp_user
    if payload.smtp_tls is not None:
        s.smtp_tls = payload.smtp_tls
    if payload.consent_version is not None:
        s.consent_version = payload.consent_version
    if payload.retention_days is not None:
        s.retention_days = payload.retention_days
    if payload.auto_verify is not None:
        s.auto_verify = payload.auto_verify
    if payload.llm_provider is not None:
        s.llm_provider = payload.llm_provider

    await db.commit()
    return {"message": "Settings updated"}


# ─── Users (admin) ────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    if current_user.role not in (UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if u.role else "recruiter",
            "is_active": u.is_active,
            "email_verified": u.email_verified,
            "last_login": u.last_login,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
async def create_user(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    if current_user.role not in (UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.core.security import hash_password
    existing = await db.execute(select(User).where(User.email == payload.get("email")))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")

    user = User(
        organization_id=current_user.organization_id,
        email=payload.get("email"),
        full_name=payload.get("full_name", ""),
        hashed_password=hash_password(payload.get("password", "")),
        role=UserRole(payload.get("role", "recruiter")),
    )
    db.add(user)
    await db.commit()
    return {"id": user.id, "message": "User created"}
