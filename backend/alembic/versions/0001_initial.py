"""initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("email_verified", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("super_admin", "org_admin", "recruiter", "reviewer", name="userrole"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("email_verified", sa.Boolean(), nullable=True, default=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        sa.Column("phone_encrypted", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("skills", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum(
            "pending_consent", "consent_granted", "consent_declined",
            "verification_in_progress", "verification_complete", "report_ready",
            name="candidatestatus"
        ), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("file_type", sa.String(20), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.String(50), nullable=True, default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id"),
    )

    op.create_table(
        "consents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=True, default=False),
        sa.Column("declined", sa.Boolean(), nullable=True, default=False),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("consent_version", sa.String(20), nullable=True, default="1.0"),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id"),
        sa.UniqueConstraint("token"),
    )

    op.create_table(
        "employment_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("start_date", sa.String(50), nullable=True),
        sa.Column("end_date", sa.String(50), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True, default=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("verification_status", sa.Enum(
            "pending", "sent", "opened", "replied", "verified", "failed", "expired",
            name="verificationstatus"
        ), nullable=True),
        sa.Column("verified_title", sa.String(255), nullable=True),
        sa.Column("verified_dates", sa.String(255), nullable=True),
        sa.Column("verifier_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "education_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("institution_name", sa.String(255), nullable=False),
        sa.Column("degree", sa.String(255), nullable=True),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("start_year", sa.String(10), nullable=True),
        sa.Column("end_year", sa.String(10), nullable=True),
        sa.Column("gpa", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("verification_status", sa.Enum(
            "pending", "sent", "opened", "replied", "verified", "failed", "expired",
            name="verificationstatus"
        ), nullable=True),
        sa.Column("verifier_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "verification_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("employment_record_id", sa.String(), nullable=True),
        sa.Column("education_record_id", sa.String(), nullable=True),
        sa.Column("verification_type", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email_subject", sa.Text(), nullable=True),
        sa.Column("email_body", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum(
            "pending", "sent", "opened", "replied", "verified", "failed", "expired",
            name="verificationstatus"
        ), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("reminder_1_sent", sa.Boolean(), nullable=True, default=False),
        sa.Column("reminder_2_sent", sa.Boolean(), nullable=True, default=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("token", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["employment_record_id"], ["employment_records.id"]),
        sa.ForeignKeyConstraint(["education_record_id"], ["education_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    op.create_table(
        "verification_responses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("responder_name", sa.String(255), nullable=True),
        sa.Column("responder_email", sa.String(255), nullable=True),
        sa.Column("responder_title", sa.String(255), nullable=True),
        sa.Column("employed_confirmed", sa.Boolean(), nullable=True),
        sa.Column("job_title_confirmed", sa.String(255), nullable=True),
        sa.Column("dates_confirmed", sa.String(255), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["verification_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "fraud_flags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("flag_type", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.Enum("low", "medium", "high", "critical", name="fraudseverity"), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "risk_scores",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("risk_level", sa.Enum("low", "moderate", "high", "critical", name="risklevel"), nullable=True),
        sa.Column("employment_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("education_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("fraud_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("public_check_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("final_verdict", sa.Enum("clear", "review_required", "reject", name="finalverdict"), nullable=True),
        sa.Column("ai_recommendation", sa.Text(), nullable=True),
        sa.Column("report_generated", sa.Boolean(), nullable=True, default=False),
        sa.Column("report_data", sa.LargeBinary(), nullable=True),
        sa.Column("report_generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("notification_type", sa.String(50), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True, default=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "system_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=True),
        sa.Column("smtp_user", sa.String(255), nullable=True),
        sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
        sa.Column("smtp_tls", sa.Boolean(), nullable=True, default=True),
        sa.Column("consent_version", sa.String(20), nullable=True, default="1.0"),
        sa.Column("retention_days", sa.Integer(), nullable=True, default=365),
        sa.Column("auto_verify", sa.Boolean(), nullable=True, default=True),
        sa.Column("llm_provider", sa.String(50), nullable=True, default="gemini"),
        sa.Column("custom_settings", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("risk_scores")
    op.drop_table("fraud_flags")
    op.drop_table("verification_responses")
    op.drop_table("verification_requests")
    op.drop_table("education_records")
    op.drop_table("employment_records")
    op.drop_table("consents")
    op.drop_table("resumes")
    op.drop_table("candidates")
    op.drop_table("users")
    op.drop_table("organizations")
