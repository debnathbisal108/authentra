"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Shield, Loader2, CheckCircle } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    company_name: "",
    website: "",
    company_size: "",
    industry: "",
    first_admin_name: "",
    admin_email: "",
    password: "",
    confirm_password: "",
  });

  const update = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      const { confirm_password, ...payload } = form;
      await authApi.register(payload);
      setSuccess(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-500/10 border border-green-500/20 rounded-2xl mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Check your email</h2>
          <p className="text-slate-400 mb-6">
            We sent a verification link to <strong className="text-white">{form.admin_email}</strong>.
            Click it to activate your account.
          </p>
          <button
            onClick={() => router.push("/login")}
            className="px-6 py-2.5 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg text-sm transition-colors"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-sky-500/10 border border-sky-500/20 rounded-2xl mb-4">
            <Shield className="w-7 h-7 text-sky-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Authentra <span className="text-sky-400">AI</span></h1>
          <p className="text-slate-400 text-sm mt-1">Create your organization account</p>
        </div>

        <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">Company Registration</h2>

          {error && (
            <div className="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Company Name *" value={form.company_name} onChange={(v) => update("company_name", v)} placeholder="Acme Corp" required />
              <Field label="Website" value={form.website} onChange={(v) => update("website", v)} placeholder="https://..." />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Company Size</label>
                <select
                  value={form.company_size}
                  onChange={(e) => update("company_size", e.target.value)}
                  className="w-full px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value="">Select size</option>
                  {["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"].map((s) => (
                    <option key={s} value={s}>{s} employees</option>
                  ))}
                </select>
              </div>
              <Field label="Industry" value={form.industry} onChange={(v) => update("industry", v)} placeholder="Technology" />
            </div>
            <hr className="border-slate-800" />
            <Field label="Your Full Name *" value={form.first_admin_name} onChange={(v) => update("first_admin_name", v)} placeholder="Jane Smith" required />
            <Field label="Work Email *" type="email" value={form.admin_email} onChange={(v) => update("admin_email", v)} placeholder="jane@company.com" required />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Password *" type="password" value={form.password} onChange={(v) => update("password", v)} placeholder="Min 8 characters" required />
              <Field label="Confirm Password *" type="password" value={form.confirm_password} onChange={(v) => update("confirm_password", v)} placeholder="Repeat password" required />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg text-sm transition-colors flex items-center justify-center gap-2 mt-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-sky-400 hover:text-sky-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder, required }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-colors"
      />
    </div>
  );
}
