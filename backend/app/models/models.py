import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, Enum, LargeBinary, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    RECRUITER = "recruiter"
    REVIEWER = "reviewer"


class CandidateStatus(str, PyEnum):
    PENDING_CONSENT = "pending_consent"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_DECLINED = "consent_declined"
    VERIFICATION_IN_PROGRESS = "verification_in_progress"
    VERIFICATION_COMPLETE = "verification_complete"
    REPORT_READY = "report_ready"


class VerificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class FraudSeverity(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FinalVerdict(str, PyEnum):
    CLEAR = "clear"
    REVIEW_REQUIRED = "review_required"
    REJECT = "reject"


# ─── Models ───────────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    website = Column(String(500))
    company_size = Column(String(50))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    candidates = relationship("Candidate", back_populates="organization")
    settings = relationship("SystemSettings", back_populates="organization", uselist=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.RECRUITER)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    candidates_created = relationship("Candidate", back_populates="created_by")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Encrypted PII
    full_name = Column(String(255))
    email_encrypted = Column(Text)
    phone_encrypted = Column(Text)
    linkedin_url = Column(String(500))

    # Parsed data
    skills = Column(JSON, default=list)
    raw_text = Column(Text)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.PENDING_CONSENT)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="candidates")
    created_by = relationship("User", back_populates="candidates_created")
    resume = relationship("Resume", back_populates="candidate", uselist=False)
    consent = relationship("Consent", back_populates="candidate", uselist=False)
    employment_records = relationship("EmploymentRecord", back_populates="candidate")
    education_records = relationship("EducationRecord", back_populates="candidate")
    verification_requests = relationship("VerificationRequest", back_populates="candidate")
    fraud_flags = relationship("FraudFlag", back_populates="candidate")
    risk_score = relationship("RiskScore", back_populates="candidate", uselist=False)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, unique=True)
    filename = Column(String(255))
    file_type = Column(String(20))
    file_size = Column(Integer)
    file_data = Column(LargeBinary, nullable=False)
    extracted_text = Column(Text)
    parse_status = Column(String(50), default="pending")
    parse_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="resume")


class Consent(Base):
    __tablename__ = "consents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, unique=True)
    token = Column(String(500), unique=True, nullable=False)
    granted = Column(Boolean, default=False)
    declined = Column(Boolean, default=False)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    consent_version = Column(String(20), default="1.0")
    granted_at = Column(DateTime)
    email_sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="consent")


class EmploymentRecord(Base):
    __tablename__ = "employment_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_title = Column(String(255))
    start_date = Column(String(50))
    end_date = Column(String(50))
    is_current = Column(Boolean, default=False)
    location = Column(String(255))
    description = Column(Text)
    contact_email = Column(String(255))
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verified_title = Column(String(255))
    verified_dates = Column(String(255))
    verifier_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="employment_records")
    verification_requests = relationship("VerificationRequest", back_populates="employment_record")


class EducationRecord(Base):
    __tablename__ = "education_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False)
    institution_name = Column(String(255), nullable=False)
    degree = Column(String(255))
    field_of_study = Column(String(255))
    start_year = Column(String(10))
    end_year = Column(String(10))
    gpa = Column(String(20))
    contact_email = Column(String(255))
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verifier_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="education_records")
    verification_requests = relationship("VerificationRequest", back_populates="education_record")


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False)
    employment_record_id = Column(String(36), ForeignKey("employment_records.id"), nullable=True)
    education_record_id = Column(String(36), ForeignKey("education_records.id"), nullable=True)
    verification_type = Column(String(50))  # employment / education
    contact_email = Column(String(255))
    contact_name = Column(String(255))
    email_subject = Column(Text)
    email_body = Column(Text)
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)
    reminder_1_sent = Column(Boolean, default=False)
    reminder_2_sent = Column(Boolean, default=False)
    response_text = Column(Text)
    token = Column(String(500), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="verification_requests")
    employment_record = relationship("EmploymentRecord", back_populates="verification_requests")
    education_record = relationship("EducationRecord", back_populates="verification_requests")
    responses = relationship("VerificationResponse", back_populates="request")


class VerificationResponse(Base):
    __tablename__ = "verification_responses"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    request_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=False)
    responder_name = Column(String(255))
    responder_email = Column(String(255))
    responder_title = Column(String(255))
    employed_confirmed = Column(Boolean)
    job_title_confirmed = Column(String(255))
    dates_confirmed = Column(String(255))
    additional_notes = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    request = relationship("VerificationRequest", back_populates="responses")


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False)
    flag_type = Column(String(100))
    description = Column(Text)
    severity = Column(Enum(FraudSeverity), default=FraudSeverity.LOW)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="fraud_flags")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False, unique=True)
    total_score = Column(Float, default=0.0)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    employment_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    fraud_score = Column(Float, default=0.0)
    public_check_score = Column(Float, default=0.0)
    explanation = Column(Text)
    final_verdict = Column(Enum(FinalVerdict))
    ai_recommendation = Column(Text)
    report_generated = Column(Boolean, default=False)
    report_data = Column(LargeBinary)
    report_generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="risk_score")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(255))
    details = Column(JSON, default=dict)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String(50))
    is_read = Column(Boolean, default=False)
    entity_type = Column(String(100))
    entity_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, unique=True)
    smtp_host = Column(String(255))
    smtp_port = Column(Integer)
    smtp_user = Column(String(255))
    smtp_password_encrypted = Column(Text)
    smtp_tls = Column(Boolean, default=True)
    consent_version = Column(String(20), default="1.0")
    retention_days = Column(Integer, default=365)
    auto_verify = Column(Boolean, default=True)
    llm_provider = Column(String(50), default="gemini")
    custom_settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="settings")
