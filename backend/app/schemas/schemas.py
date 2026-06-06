from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime
from app.models.models import UserRole, CandidateStatus, VerificationStatus, RiskLevel, FraudSeverity, FinalVerdict


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    first_admin_name: str
    admin_email: EmailStr
    password: str

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    organization_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.RECRUITER


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# ─── Organization ─────────────────────────────────────────────────────────────

class OrganizationResponse(BaseModel):
    id: str
    name: str
    website: Optional[str]
    company_size: Optional[str]
    industry: Optional[str]
    is_active: bool
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Candidate ────────────────────────────────────────────────────────────────

class CandidateResponse(BaseModel):
    id: str
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    linkedin_url: Optional[str]
    skills: List[str]
    status: CandidateStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateDetailResponse(CandidateResponse):
    employment_records: List["EmploymentRecordResponse"] = []
    education_records: List["EducationRecordResponse"] = []
    fraud_flags: List["FraudFlagResponse"] = []
    risk_score: Optional["RiskScoreResponse"] = None
    consent: Optional["ConsentResponse"] = None


# ─── Employment ───────────────────────────────────────────────────────────────

class EmploymentRecordResponse(BaseModel):
    id: str
    company_name: str
    job_title: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: bool
    location: Optional[str]
    contact_email: Optional[str]
    verification_status: VerificationStatus
    verified_title: Optional[str]
    verified_dates: Optional[str]
    verifier_notes: Optional[str]

    class Config:
        from_attributes = True


class EmploymentContactUpdate(BaseModel):
    contact_email: EmailStr


# ─── Education ────────────────────────────────────────────────────────────────

class EducationRecordResponse(BaseModel):
    id: str
    institution_name: str
    degree: Optional[str]
    field_of_study: Optional[str]
    start_year: Optional[str]
    end_year: Optional[str]
    contact_email: Optional[str]
    verification_status: VerificationStatus
    verifier_notes: Optional[str]

    class Config:
        from_attributes = True


class EducationContactUpdate(BaseModel):
    contact_email: EmailStr


# ─── Fraud / Risk ─────────────────────────────────────────────────────────────

class FraudFlagResponse(BaseModel):
    id: str
    flag_type: str
    description: str
    severity: FraudSeverity
    details: dict
    created_at: datetime

    class Config:
        from_attributes = True


class RiskScoreResponse(BaseModel):
    id: str
    total_score: float
    risk_level: RiskLevel
    employment_score: float
    education_score: float
    fraud_score: float
    public_check_score: float
    explanation: Optional[str]
    final_verdict: Optional[FinalVerdict]
    ai_recommendation: Optional[str]
    report_generated: bool
    report_generated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Consent ──────────────────────────────────────────────────────────────────

class ConsentResponse(BaseModel):
    id: str
    granted: bool
    declined: bool
    granted_at: Optional[datetime]
    consent_version: str
    email_sent_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Verification ─────────────────────────────────────────────────────────────

class VerificationRequestResponse(BaseModel):
    id: str
    verification_type: str
    contact_email: Optional[str]
    status: VerificationStatus
    sent_at: Optional[datetime]
    replied_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationResponseSubmit(BaseModel):
    responder_name: str
    responder_email: EmailStr
    responder_title: Optional[str] = None
    employed_confirmed: bool
    job_title_confirmed: Optional[str] = None
    dates_confirmed: Optional[str] = None
    additional_notes: Optional[str] = None


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_candidates: int
    pending_consents: int
    active_verifications: int
    completed_verifications: int
    high_risk_candidates: int


class DashboardChartData(BaseModel):
    verification_status: dict
    risk_distribution: dict


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: str
    title: str
    message: Optional[str]
    notification_type: Optional[str]
    is_read: bool
    entity_type: Optional[str]
    entity_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Audit ────────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    details: dict
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Settings ─────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: Optional[bool] = None
    consent_version: Optional[str] = None
    retention_days: Optional[int] = None
    auto_verify: Optional[bool] = None
    llm_provider: Optional[str] = None


# ─── GDPR ─────────────────────────────────────────────────────────────────────

class DataExportResponse(BaseModel):
    candidate_id: str
    exported_at: datetime
    data: dict


# Forward references
CandidateDetailResponse.model_rebuild()
