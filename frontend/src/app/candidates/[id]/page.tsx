"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import { candidatesApi } from "@/lib/api";
import { Candidate } from "@/types";
import {
  Card, CardHeader, CardTitle, CardContent, Badge, Button, Spinner,
} from "@/components/ui";
import {
  statusConfig, riskConfig, verdictConfig, severityConfig,
  verificationStatusConfig, formatDate, formatDateTime, cn,
} from "@/lib/utils";
import {
  ArrowLeft, Download, Send, Mail, Building2, GraduationCap,
  AlertTriangle, BarChart2, User, CheckCircle, XCircle, Clock,
} from "lucide-react";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [contactEdits, setContactEdits] = useState<Record<string, string>>({});

  useEffect(() => {
    candidatesApi.get(id).then((res) => setCandidate(res.data)).finally(() => setLoading(false));
  }, [id]);

  const downloadReport = async () => {
    setActionLoading("report");
    try {
      const res = await candidatesApi.downloadReport(id);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `authentra_report_${candidate?.full_name?.replace(/\s/g, "_") || id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Report not ready yet");
    } finally {
      setActionLoading("");
    }
  };

  const sendVerifications = async () => {
    setActionLoading("verify");
    try {
      await candidatesApi.sendVerifications(id);
      alert("Verification emails will be sent shortly");
      const res = await candidatesApi.get(id);
      setCandidate(res.data);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to send verifications");
    } finally {
      setActionLoading("");
    }
  };

  const saveContact = async (type: "employment" | "education", recordId: string) => {
    const email = contactEdits[recordId];
    if (!email) return;
    try {
      if (type === "employment") {
        await candidatesApi.updateEmploymentContact(id, recordId, email);
      } else {
        await candidatesApi.updateEducationContact(id, recordId, email);
      }
      const res = await candidatesApi.get(id);
      setCandidate(res.data);
      setContactEdits((prev) => { const n = {...prev}; delete n[recordId]; return n; });
    } catch {}
  };

  if (loading) {
    return <AuthGuard><div className="flex items-center justify-center h-64"><Spinner /></div></AuthGuard>;
  }

  if (!candidate) {
    return <AuthGuard><div className="p-6 text-center text-slate-500">Candidate not found</div></AuthGuard>;
  }

  const sc = statusConfig[candidate.status as keyof typeof statusConfig];
  const rs = candidate.risk_score;
  const riskCfg = rs ? riskConfig[rs.risk_level] : null;
  const verdictCfg = rs?.final_verdict ? verdictConfig[rs.final_verdict] : null;

  return (
    <AuthGuard>
      <div className="p-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-500">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900">{candidate.full_name || "Processing..."}</h1>
                <Badge className={sc?.color || "bg-slate-100 text-slate-600"}>{sc?.label || candidate.status}</Badge>
              </div>
              <p className="text-sm text-slate-500 mt-0.5">{candidate.email || "Email not extracted yet"}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {candidate.status === "consent_granted" && (
              <Button onClick={sendVerifications} loading={actionLoading === "verify"} variant="outline" size="sm">
                <Send className="w-3.5 h-3.5" /> Send Verifications
              </Button>
            )}
            {candidate.risk_score?.report_generated && (
              <Button onClick={downloadReport} loading={actionLoading === "report"} size="sm">
                <Download className="w-3.5 h-3.5" /> Download Report
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="space-y-4">
            {/* Profile */}
            <Card>
              <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Row icon={<User className="w-3.5 h-3.5" />} label="Name" value={candidate.full_name} />
                <Row icon={<Mail className="w-3.5 h-3.5" />} label="Email" value={candidate.email} />
                <Row icon={<User className="w-3.5 h-3.5" />} label="Phone" value={candidate.phone} />
                {candidate.linkedin_url && (
                  <div>
                    <p className="text-xs text-slate-500">LinkedIn</p>
                    <a href={candidate.linkedin_url} target="_blank" className="text-sm text-sky-500 hover:text-sky-600 truncate block">
                      {candidate.linkedin_url}
                    </a>
                  </div>
                )}
                {candidate.skills?.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1.5">Skills</p>
                    <div className="flex flex-wrap gap-1">
                      {candidate.skills.map((s) => <Badge key={s} className="bg-sky-50 text-sky-700">{s}</Badge>)}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Consent */}
            <Card>
              <CardHeader><CardTitle>Consent Status</CardTitle></CardHeader>
              <CardContent>
                {candidate.consent?.granted ? (
                  <div className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="w-4 h-4" />
                    <div>
                      <p className="text-sm font-medium">Granted</p>
                      <p className="text-xs text-slate-400">{formatDateTime(candidate.consent.granted_at)}</p>
                    </div>
                  </div>
                ) : candidate.consent?.declined ? (
                  <div className="flex items-center gap-2 text-red-600">
                    <XCircle className="w-4 h-4" />
                    <p className="text-sm font-medium">Declined</p>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-yellow-600">
                    <Clock className="w-4 h-4" />
                    <div>
                      <p className="text-sm font-medium">Awaiting Response</p>
                      {candidate.consent?.email_sent_at && (
                        <p className="text-xs text-slate-400">Sent {formatDateTime(candidate.consent.email_sent_at)}</p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Risk Score */}
            {rs && (
              <Card className={cn("border", riskCfg?.bg)}>
                <CardHeader><CardTitle>Risk Assessment</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className={cn("text-3xl font-bold", riskCfg?.color)}>{Math.round(rs.total_score)}</span>
                    <Badge className={cn(riskCfg?.color, riskCfg?.bg, "border")}>{riskCfg?.label}</Badge>
                  </div>
                  {verdictCfg && (
                    <div>
                      <p className="text-xs text-slate-500">Final Verdict</p>
                      <p className={cn("text-sm font-bold", verdictCfg.color)}>{verdictCfg.label}</p>
                    </div>
                  )}
                  <div className="space-y-1.5">
                    {[
                      { label: "Employment", val: rs.employment_score },
                      { label: "Education", val: rs.education_score },
                      { label: "Fraud", val: rs.fraud_score },
                      { label: "Public", val: rs.public_check_score },
                    ].map(({ label, val }) => (
                      <div key={label}>
                        <div className="flex justify-between text-xs text-slate-500 mb-0.5">
                          <span>{label}</span><span>{Math.round(val)}</span>
                        </div>
                        <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full transition-all", val > 75 ? "bg-red-400" : val > 50 ? "bg-orange-400" : val > 25 ? "bg-yellow-400" : "bg-green-400")}
                            style={{ width: `${val}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  {rs.ai_recommendation && (
                    <p className="text-xs text-slate-600 border-t border-slate-200 pt-2 mt-2">{rs.ai_recommendation}</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column */}
          <div className="lg:col-span-2 space-y-4">
            {/* Employment */}
            <Card>
              <CardHeader className="flex flex-row items-center gap-2">
                <Building2 className="w-4 h-4 text-slate-400" />
                <CardTitle>Employment History</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {candidate.employment_records?.length === 0 ? (
                  <div className="px-6 py-4 text-sm text-slate-400">No employment records extracted</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {candidate.employment_records?.map((emp) => {
                      const vs = verificationStatusConfig[emp.verification_status] || verificationStatusConfig.pending;
                      return (
                        <div key={emp.id} className="px-6 py-4">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <p className="text-sm font-semibold text-slate-900">{emp.company_name}</p>
                              <p className="text-xs text-slate-500">{emp.job_title} · {emp.start_date} – {emp.is_current ? "Present" : emp.end_date || "?"}</p>
                            </div>
                            <Badge className={vs.color}>{vs.label}</Badge>
                          </div>
                          {emp.verifier_notes && (
                            <p className="text-xs text-slate-600 bg-slate-50 rounded p-2 mt-2">{emp.verifier_notes}</p>
                          )}
                          <div className="mt-2 flex items-center gap-2">
                            <input
                              type="email"
                              value={contactEdits[emp.id] ?? emp.contact_email ?? ""}
                              onChange={(e) => setContactEdits((p) => ({ ...p, [emp.id]: e.target.value }))}
                              placeholder="HR contact email"
                              className="flex-1 text-xs px-2.5 py-1.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500"
                            />
                            {contactEdits[emp.id] !== undefined && contactEdits[emp.id] !== emp.contact_email && (
                              <Button size="sm" variant="outline" onClick={() => saveContact("employment", emp.id)}>Save</Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Education */}
            <Card>
              <CardHeader className="flex flex-row items-center gap-2">
                <GraduationCap className="w-4 h-4 text-slate-400" />
                <CardTitle>Education</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {candidate.education_records?.length === 0 ? (
                  <div className="px-6 py-4 text-sm text-slate-400">No education records extracted</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {candidate.education_records?.map((edu) => {
                      const vs = verificationStatusConfig[edu.verification_status] || verificationStatusConfig.pending;
                      return (
                        <div key={edu.id} className="px-6 py-4">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <p className="text-sm font-semibold text-slate-900">{edu.institution_name}</p>
                              <p className="text-xs text-slate-500">
                                {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")} · {edu.start_year} – {edu.end_year}
                              </p>
                            </div>
                            <Badge className={vs.color}>{vs.label}</Badge>
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <input
                              type="email"
                              value={contactEdits[edu.id] ?? edu.contact_email ?? ""}
                              onChange={(e) => setContactEdits((p) => ({ ...p, [edu.id]: e.target.value }))}
                              placeholder="Registrar/admissions email"
                              className="flex-1 text-xs px-2.5 py-1.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500"
                            />
                            {contactEdits[edu.id] !== undefined && contactEdits[edu.id] !== edu.contact_email && (
                              <Button size="sm" variant="outline" onClick={() => saveContact("education", edu.id)}>Save</Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Fraud Flags */}
            {(candidate.fraud_flags?.length || 0) > 0 && (
              <Card className="border-orange-200">
                <CardHeader className="flex flex-row items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  <CardTitle>Fraud & Anomaly Flags</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-slate-100">
                    {candidate.fraud_flags?.map((flag) => {
                      const sc = severityConfig[flag.severity as keyof typeof severityConfig];
                      return (
                        <div key={flag.id} className="px-6 py-3 flex items-start gap-3">
                          <Badge className={sc?.color || "bg-slate-100 text-slate-600"}>{sc?.label || flag.severity}</Badge>
                          <div>
                            <p className="text-xs font-semibold text-slate-700">{flag.flag_type.replace(/_/g, " ")}</p>
                            <p className="text-xs text-slate-500">{flag.description}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}

function Row({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm text-slate-800 font-medium">{value}</p>
    </div>
  );
}
