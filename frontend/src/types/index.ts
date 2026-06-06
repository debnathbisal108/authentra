export type CandidateStatus =
  | "pending_consent"
  | "consent_granted"
  | "consent_declined"
  | "verification_in_progress"
  | "verification_complete"
  | "report_ready";

export type VerificationStatus =
  | "pending" | "sent" | "opened" | "replied" | "verified" | "failed" | "expired";

export type RiskLevel = "low" | "moderate" | "high" | "critical";
export type FinalVerdict = "clear" | "review_required" | "reject";
export type FraudSeverity = "low" | "medium" | "high" | "critical";

export interface Candidate {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  skills: string[];
  status: CandidateStatus;
  created_at: string;
  updated_at: string;
  employment_records?: EmploymentRecord[];
  education_records?: EducationRecord[];
  fraud_flags?: FraudFlag[];
  risk_score?: RiskScore | null;
  consent?: ConsentRecord | null;
}

export interface EmploymentRecord {
  id: string;
  company_name: string;
  job_title: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  location: string | null;
  contact_email: string | null;
  verification_status: VerificationStatus;
  verified_title: string | null;
  verified_dates: string | null;
  verifier_notes: string | null;
}

export interface EducationRecord {
  id: string;
  institution_name: string;
  degree: string | null;
  field_of_study: string | null;
  start_year: string | null;
  end_year: string | null;
  contact_email: string | null;
  verification_status: VerificationStatus;
  verifier_notes: string | null;
}

export interface FraudFlag {
  id: string;
  flag_type: string;
  description: string;
  severity: FraudSeverity;
  details: Record<string, unknown>;
  created_at: string;
}

export interface RiskScore {
  id: string;
  total_score: number;
  risk_level: RiskLevel;
  employment_score: number;
  education_score: number;
  fraud_score: number;
  public_check_score: number;
  explanation: string | null;
  final_verdict: FinalVerdict | null;
  ai_recommendation: string | null;
  report_generated: boolean;
  report_generated_at: string | null;
}

export interface ConsentRecord {
  id: string;
  granted: boolean;
  declined: boolean;
  granted_at: string | null;
  consent_version: string;
  email_sent_at: string | null;
}

export interface DashboardStats {
  total_candidates: number;
  pending_consents: number;
  active_verifications: number;
  completed_verifications: number;
  high_risk_candidates: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string | null;
  notification_type: string | null;
  is_read: boolean;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}
