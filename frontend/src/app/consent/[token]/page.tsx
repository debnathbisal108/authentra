"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { consentApi } from "@/lib/api";
import { Shield, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function ConsentPage() {
  const { token } = useParams<{ token: string }>();
  const searchParams = useSearchParams();
  const action = searchParams.get("action");

  const [info, setInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    consentApi.getInfo(token)
      .then((res) => setInfo(res.data))
      .catch(() => setError("Invalid or expired consent link"))
      .finally(() => setLoading(false));
  }, [token]);

  // Auto-respond if action is in URL
  useEffect(() => {
    if (info && !info.already_responded && action && (action === "accept" || action === "decline")) {
      handleResponse(action as "accept" | "decline");
    }
  }, [info, action]);

  const handleResponse = async (act: "accept" | "decline") => {
    setResponding(true);
    try {
      const res = await consentApi.respond(token, act);
      setResult({ success: true, message: res.data.message });
    } catch (err: any) {
      setResult({ success: false, message: err?.response?.data?.detail || "Something went wrong" });
    } finally {
      setResponding(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 mb-2">
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
          ) : result ? (
            <div className="text-center py-8">
              {result.success ? (
                <>
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                  <h2 className="text-lg font-semibold text-slate-800 mb-2">Thank You</h2>
                  <p className="text-slate-500 text-sm">{result.message}</p>
                </>
              ) : (
                <>
                  <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
                  <h2 className="text-lg font-semibold text-slate-800 mb-2">Something went wrong</h2>
                  <p className="text-slate-500 text-sm">{result.message}</p>
                </>
              )}
            </div>
          ) : info?.already_responded ? (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Already Responded</h2>
              <p className="text-slate-500 text-sm">
                You have already {info.granted ? "accepted" : "declined"} this verification request.
              </p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900 mb-1">Background Verification Consent</h2>
                <p className="text-sm text-slate-500">
                  <strong className="text-slate-700">{info?.organization_name}</strong> has requested a background check for{" "}
                  <strong className="text-slate-700">{info?.candidate_name}</strong>.
                </p>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 mb-6 space-y-2 text-sm">
                <p className="font-semibold text-slate-700 mb-3">What will be verified:</p>
                {["Employment history (dates, titles, companies)", "Educational background (degrees, institutions)", "Public records (sanctions, watchlists)"].map((item) => (
                  <div key={item} className="flex items-start gap-2 text-slate-600">
                    <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>

              <div className="bg-sky-50 border border-sky-100 rounded-xl p-4 mb-6 text-xs text-slate-600 space-y-1">
                <p className="font-semibold text-slate-700">Your rights:</p>
                <p>• You may decline this request at any time.</p>
                <p>• Your data is stored securely and deleted per our retention policy.</p>
                <p>• You may request data export or deletion at any time.</p>
                <p>• Consent version 1.0 — this verification complies with applicable data protection laws.</p>
              </div>

              {responding ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
                  <span className="ml-2 text-sm text-slate-500">Processing...</span>
                </div>
              ) : (
                <div className="flex gap-3">
                  <button
                    onClick={() => handleResponse("accept")}
                    className="flex-1 py-3 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Accept Verification
                  </button>
                  <button
                    onClick={() => handleResponse("decline")}
                    className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
                  >
                    <XCircle className="w-4 h-4" />
                    Decline
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
