"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { candidatesApi } from "@/lib/api";
import { Card, CardContent, Badge, Button, Spinner, PageHeader, EmptyState } from "@/components/ui";
import { riskConfig, verdictConfig, formatDateTime, cn } from "@/lib/utils";
import { FileText, Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { Candidate } from "@/types";

export default function ReportsPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string>("");

  useEffect(() => {
    candidatesApi.list({ status: "report_ready", limit: 100 })
      .then((res) => setCandidates(res.data))
      .finally(() => setLoading(false));
  }, []);

  const download = async (candidate: Candidate) => {
    setDownloading(candidate.id);
    try {
      const res = await candidatesApi.downloadReport(candidate.id);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `authentra_report_${(candidate.full_name || "candidate").replace(/\s/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Report not available");
    } finally {
      setDownloading("");
    }
  };

  return (
    <AuthGuard>
      <div className="p-6 max-w-7xl mx-auto">
        <PageHeader title="Reports" description="Download completed background verification reports" />

        <Card>
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : candidates.length === 0 ? (
            <EmptyState
              icon={<FileText className="w-full h-full" />}
              title="No reports ready"
              description="Reports appear here once background verifications are complete"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100">
                    {["Candidate", "Email", "Risk Level", "Verdict", "Completed", ""].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {candidates.map((c) => {
                    const rs = (c as any).risk_score;
                    const rc = rs?.risk_level ? riskConfig[rs.risk_level as keyof typeof riskConfig] : null;
                    const vc = rs?.final_verdict ? verdictConfig[rs.final_verdict as keyof typeof verdictConfig] : null;
                    return (
                      <tr key={c.id} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3">
                          <Link href={`/candidates/${c.id}`} className="text-sm font-medium text-sky-600 hover:text-sky-700">
                            {c.full_name || "Unknown"}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">{c.email || "—"}</td>
                        <td className="px-4 py-3">
                          {rc ? <Badge className={cn(rc.color, rc.bg, "border")}>{rc.label}</Badge> : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {vc ? <span className={cn("text-sm font-semibold", vc.color)}>{vc.label}</span> : "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">{formatDateTime(c.updated_at)}</td>
                        <td className="px-4 py-3">
                          <Button
                            size="sm"
                            variant="outline"
                            loading={downloading === c.id}
                            onClick={() => download(c)}
                          >
                            <Download className="w-3.5 h-3.5" />
                            PDF
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AuthGuard>
  );
}
