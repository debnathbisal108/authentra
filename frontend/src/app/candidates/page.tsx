"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { candidatesApi } from "@/lib/api";
import { Card, CardContent, Badge, Button, PageHeader, EmptyState, Spinner } from "@/components/ui";
import { Candidate, CandidateStatus } from "@/types";
import { statusConfig, formatDate, cn } from "@/lib/utils";
import { Upload, Users, Search, ChevronRight, X, Loader2, FileText, AlertCircle } from "lucide-react";
import Link from "next/link";

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await candidatesApi.list({ limit: 100, status: statusFilter || undefined });
      setCandidates(res.data);
    } catch {}
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (file: File) => {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "doc"].includes(ext || "")) {
      setUploadError("Only PDF and DOCX files are supported");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError("File too large (max 10MB)");
      return;
    }
    setUploadError("");
    setUploading(true);
    const fd = new FormData();
    fd.append("resume", file);
    try {
      await candidatesApi.upload(fd);
      await load();
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const filtered = candidates.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.full_name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.status?.includes(q)
    );
  });

  return (
    <AuthGuard>
      <div className="p-6 max-w-7xl mx-auto">
        <PageHeader
          title="Candidates"
          description="Upload resumes to start background verifications"
          action={
            <Button onClick={() => fileRef.current?.click()} loading={uploading}>
              <Upload className="w-4 h-4" />
              Upload Resume
            </Button>
          }
        />

        {/* Upload Zone */}
        <div
          className={cn(
            "border-2 border-dashed rounded-xl p-8 text-center mb-6 transition-colors cursor-pointer",
            dragOver ? "border-sky-400 bg-sky-50" : "border-slate-200 bg-slate-50 hover:border-sky-300 hover:bg-sky-50/50"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleUpload(file);
          }}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
              <p className="text-sm text-slate-600">Uploading and processing resume…</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <FileText className="w-8 h-8 text-slate-400" />
              <p className="text-sm font-medium text-slate-600">Drop resume here or click to browse</p>
              <p className="text-xs text-slate-400">Supports PDF and DOCX · Max 10MB</p>
            </div>
          )}
        </div>

        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />

        {uploadError && (
          <div className="mb-4 flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {uploadError}
            <button className="ml-auto" onClick={() => setUploadError("")}><X className="w-3 h-3" /></button>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-3 mb-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search candidates..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
          >
            <option value="">All Statuses</option>
            {Object.entries(statusConfig).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <Card>
          {loading ? (
            <div className="flex items-center justify-center py-16"><Spinner /></div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Users className="w-full h-full" />}
              title="No candidates yet"
              description="Upload a resume to get started with background verification"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100">
                    {["Candidate", "Email", "Status", "Skills", "Created", ""].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filtered.map((c) => {
                    const sc = statusConfig[c.status as CandidateStatus] || { label: c.status, color: "bg-slate-100 text-slate-600" };
                    return (
                      <tr key={c.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-slate-900">{c.full_name || <span className="text-slate-400 italic">Parsing...</span>}</p>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">{c.email || "—"}</td>
                        <td className="px-4 py-3">
                          <Badge className={sc.color}>{sc.label}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {c.skills?.slice(0, 3).map((s) => (
                              <Badge key={s} className="bg-slate-100 text-slate-600">{s}</Badge>
                            ))}
                            {(c.skills?.length || 0) > 3 && (
                              <Badge className="bg-slate-100 text-slate-500">+{c.skills.length - 3}</Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">{formatDate(c.created_at)}</td>
                        <td className="px-4 py-3">
                          <Link href={`/candidates/${c.id}`}>
                            <Button variant="ghost" size="sm">
                              View <ChevronRight className="w-3.5 h-3.5" />
                            </Button>
                          </Link>
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
