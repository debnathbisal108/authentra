"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { candidatesApi } from "@/lib/api";
import { Card, CardContent, Badge, Spinner, PageHeader, EmptyState } from "@/components/ui";
import { verificationStatusConfig, formatDateTime, cn } from "@/lib/utils";
import { CheckSquare, Building2, GraduationCap } from "lucide-react";
import Link from "next/link";

interface VerificationItem {
  candidateId: string;
  candidateName: string | null;
  type: "employment" | "education";
  entityName: string;
  status: string;
  contactEmail: string | null;
  updatedAt: string;
}

export default function VerificationsPage() {
  const [items, setItems] = useState<VerificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const res = await candidatesApi.list({ limit: 200 });
        const candidates = res.data;
        const verifs: VerificationItem[] = [];

        for (const c of candidates) {
          try {
            const detail = await candidatesApi.get(c.id);
            const d = detail.data;
            for (const emp of d.employment_records || []) {
              verifs.push({
                candidateId: c.id,
                candidateName: c.full_name,
                type: "employment",
                entityName: emp.company_name,
                status: emp.verification_status,
                contactEmail: emp.contact_email,
                updatedAt: emp.updated_at || c.updated_at,
              });
            }
            for (const edu of d.education_records || []) {
              verifs.push({
                candidateId: c.id,
                candidateName: c.full_name,
                type: "education",
                entityName: edu.institution_name,
                status: edu.verification_status,
                contactEmail: edu.contact_email,
                updatedAt: edu.updated_at || c.updated_at,
              });
            }
          } catch {}
        }
        setItems(verifs);
      } catch {}
      setLoading(false);
    }
    load();
  }, []);

  const filtered = filter
    ? items.filter((i) => i.status === filter)
    : items;

  const counts = items.reduce((acc, i) => {
    acc[i.status] = (acc[i.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <AuthGuard>
      <div className="p-6 max-w-7xl mx-auto">
        <PageHeader title="Verifications" description="Track all employment and education verification requests" />

        {/* Summary chips */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setFilter("")}
            className={cn("px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              !filter ? "bg-sky-500 text-white" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50")}
          >
            All ({items.length})
          </button>
          {Object.entries(verificationStatusConfig).map(([k, v]) => {
            if (!counts[k]) return null;
            return (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={cn("px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  filter === k ? "bg-sky-500 text-white" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50")}
              >
                {v.label} ({counts[k]})
              </button>
            );
          })}
        </div>

        <Card>
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<CheckSquare className="w-full h-full" />}
              title="No verifications yet"
              description="Verifications appear here once candidates grant consent and verification emails are sent"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100">
                    {["Type", "Candidate", "Entity", "Contact Email", "Status", "Updated"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filtered.map((item, idx) => {
                    const vs = verificationStatusConfig[item.status as keyof typeof verificationStatusConfig] || verificationStatusConfig.pending;
                    return (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            {item.type === "employment"
                              ? <Building2 className="w-3.5 h-3.5 text-sky-500" />
                              : <GraduationCap className="w-3.5 h-3.5 text-purple-500" />}
                            <span className="text-xs text-slate-600 capitalize">{item.type}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/candidates/${item.candidateId}`} className="text-sm text-sky-600 hover:text-sky-700 font-medium">
                            {item.candidateName || "Processing..."}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700">{item.entityName}</td>
                        <td className="px-4 py-3 text-xs text-slate-500">{item.contactEmail || <span className="italic text-slate-400">Not set</span>}</td>
                        <td className="px-4 py-3">
                          <Badge className={vs.color}>{vs.label}</Badge>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">{formatDateTime(item.updatedAt)}</td>
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
