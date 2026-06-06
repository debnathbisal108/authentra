import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { CandidateStatus, RiskLevel, FinalVerdict, FraudSeverity, VerificationStatus } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export const statusConfig: Record<CandidateStatus, { label: string; color: string }> = {
  pending_consent: { label: "Pending Consent", color: "bg-yellow-100 text-yellow-800" },
  consent_granted: { label: "Consent Granted", color: "bg-blue-100 text-blue-800" },
  consent_declined: { label: "Consent Declined", color: "bg-red-100 text-red-800" },
  verification_in_progress: { label: "In Progress", color: "bg-purple-100 text-purple-800" },
  verification_complete: { label: "Complete", color: "bg-green-100 text-green-800" },
  report_ready: { label: "Report Ready", color: "bg-emerald-100 text-emerald-800" },
};

export const riskConfig: Record<RiskLevel, { label: string; color: string; bg: string }> = {
  low: { label: "Low Risk", color: "text-green-700", bg: "bg-green-50 border-green-200" },
  moderate: { label: "Moderate Risk", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200" },
  high: { label: "High Risk", color: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
  critical: { label: "Critical Risk", color: "text-red-700", bg: "bg-red-50 border-red-200" },
};

export const verdictConfig: Record<FinalVerdict, { label: string; color: string }> = {
  clear: { label: "Clear", color: "text-green-700" },
  review_required: { label: "Review Required", color: "text-yellow-700" },
  reject: { label: "Reject", color: "text-red-700" },
};

export const severityConfig: Record<FraudSeverity, { label: string; color: string }> = {
  low: { label: "Low", color: "text-blue-700 bg-blue-50" },
  medium: { label: "Medium", color: "text-yellow-700 bg-yellow-50" },
  high: { label: "High", color: "text-orange-700 bg-orange-50" },
  critical: { label: "Critical", color: "text-red-700 bg-red-50" },
};

export const verificationStatusConfig: Record<VerificationStatus, { label: string; color: string }> = {
  pending: { label: "Pending", color: "text-gray-600 bg-gray-100" },
  sent: { label: "Sent", color: "text-blue-600 bg-blue-100" },
  opened: { label: "Opened", color: "text-purple-600 bg-purple-100" },
  replied: { label: "Replied", color: "text-teal-600 bg-teal-100" },
  verified: { label: "Verified", color: "text-green-700 bg-green-100" },
  failed: { label: "Failed", color: "text-red-700 bg-red-100" },
  expired: { label: "Expired", color: "text-gray-500 bg-gray-100" },
};
