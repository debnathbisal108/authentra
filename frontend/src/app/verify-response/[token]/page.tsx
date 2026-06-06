"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { verifyResponseApi } from "@/lib/api";
import { Shield, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function VerifyResponsePage() {
  const { token } = useParams<{ token: string }>();
  const [formData, setFormData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    responder_name: "",
    responder_email: "",
    responder_title: "",
    employed_confirmed: true,
    job_title_confirmed: "",
    dates_confirmed: "",
    additional_notes: "",
  });

  useEffect(() => {
    verifyResponseApi.getForm(token)
      .then((res) => setFormData(res.data))
      .catch(() => setError("Invalid or expired verification link"))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await verifyResponseApi.submit(token, form);
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const update = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2">
            <div className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-slate-900">Authentra <span className="text-sky-500">AI</span></span>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Invalid Link</h2>
              <p className="text-slate-500 text-sm">{error}</p>
            </div>
          ) : formData?.already_responded ? (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Already Responded</h2>
              <p className="text-slate-500 text-sm">Your response has already been recorded. Thank you.</p>
            </div>
          ) : done ? (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Thank You!</h2>
              <p className="text-slate-500 text-sm">Your response has been recorded successfully.</p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900 mb-1">
                  {formData?.verification_type === "education" ? "Education" : "Employment"} Verification
                </h2>
                <p className="text-sm text-slate-500">
                  Please verify the following information for{" "}
                  <strong className="text-slate-700">{formData?.candidate_name}</strong>
                  {formData?.entity_name && (
                    <> at <strong className="text-slate-700">{formData?.entity_name}</strong></>
                  )}.
                </p>
                {formData?.email_body && (
                  <div className="mt-3 p-3 bg-slate-50 rounded-lg text-xs text-slate-600 whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {formData.email_body}
                  </div>
                )}
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="Your Full Name *" value={form.responder_name} onChange={(v) => update("responder_name", v)} placeholder="Jane Smith" required />
                <Field label="Your Email *" type="email" value={form.responder_email} onChange={(v) => update("responder_email", v)} placeholder="hr@company.com" required />
                <Field label="Your Title/Position" value={form.responder_title} onChange={(v) => update("responder_title", v)} placeholder="HR Manager" />

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Did {formData?.candidate_name} work / attend here? *
                  </label>
                  <div className="flex gap-3">
                    {[{ label: "Yes, confirmed", value: true }, { label: "No, not found", value: false }].map(({ label, value }) => (
                      <label key={label} className={`flex-1 flex items-center gap-2 p-3 border rounded-xl cursor-pointer transition-colors ${
                        form.employed_confirmed === value ? "border-sky-400 bg-sky-50" : "border-slate-200 hover:border-slate-300"
                      }`}>
                        <input
                          type="radio"
                          name="confirmed"
                          checked={form.employed_confirmed === value}
                          onChange={() => update("employed_confirmed", value)}
                          className="text-sky-500"
                        />
                        <span className="text-sm text-slate-700">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {form.employed_confirmed && (
                  <>
                    <Field label="Confirmed Title/Degree" value={form.job_title_confirmed} onChange={(v) => update("job_title_confirmed", v)} placeholder="Senior Engineer / BSc Computer Science" />
                    <Field label="Confirmed Dates" value={form.dates_confirmed} onChange={(v) => update("dates_confirmed", v)} placeholder="Jan 2020 – Dec 2022" />
                  </>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Additional Notes</label>
                  <textarea
                    value={form.additional_notes}
                    onChange={(e) => update("additional_notes", e.target.value)}
                    placeholder="Any additional information or comments..."
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {submitting ? "Submitting..." : "Submit Verification"}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-slate-400 mt-4">
          This verification is powered by Authentra AI. Your response is voluntary and will be kept confidential.
        </p>
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
      <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 transition-colors"
      />
    </div>
  );
}
