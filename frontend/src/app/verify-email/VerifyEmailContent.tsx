"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";
import { Shield, CheckCircle, XCircle, Loader2 } from "lucide-react";
import Link from "next/link";

export default function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<
    "loading" | "success" | "error"
  >("loading");

  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided");
      return;
    }

    authApi
      .verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.data.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(
          err?.response?.data?.detail ||
            "Verification failed or link expired"
        );
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center gap-2 mb-8">
          <div className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white">
            Authentra <span className="text-sky-400">AI</span>
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8">
          {status === "loading" && (
            <>
              <Loader2 className="w-10 h-10 text-sky-500 animate-spin mx-auto mb-4" />
              <h2 className="text-white font-semibold">
                Verifying your email...
              </h2>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="w-10 h-10 text-green-400 mx-auto mb-4" />
              <h2 className="text-white font-semibold text-lg mb-2">
                Email Verified!
              </h2>
              <p className="text-slate-400 text-sm mb-6">{message}</p>

              <Link
                href="/login"
                className="inline-block px-6 py-2.5 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg text-sm transition-colors"
              >
                Sign In Now
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
              <h2 className="text-white font-semibold text-lg mb-2">
                Verification Failed
              </h2>
              <p className="text-slate-400 text-sm mb-6">{message}</p>

              <Link
                href="/register"
                className="inline-block px-6 py-2.5 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg text-sm transition-colors"
              >
                Back to Register
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
