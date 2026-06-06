"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { settingsApi } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, Button, Input, PageHeader } from "@/components/ui";
import { CheckCircle } from "lucide-react";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState<Record<string, any>>({});

  useEffect(() => {
    settingsApi.get().then((res) => {
      setSettings(res.data);
      setForm(res.data);
    }).finally(() => setLoading(false));
  }, []);

  const update = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await settingsApi.update(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
    setSaving(false);
  };

  if (loading) return <AuthGuard><div className="flex items-center justify-center h-64 text-slate-400">Loading...</div></AuthGuard>;

  return (
    <AuthGuard>
      <div className="p-6 max-w-3xl mx-auto">
        <PageHeader
          title="Settings"
          description="Configure your organization's verification settings"
          action={
            <Button onClick={save} loading={saving}>
              {saved && <CheckCircle className="w-4 h-4" />}
              {saved ? "Saved!" : "Save Changes"}
            </Button>
          }
        />

        <div className="space-y-6">
          {/* Email */}
          <Card>
            <CardHeader><CardTitle>Email (SMTP) Configuration</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="SMTP Host"
                  value={form.smtp_host || ""}
                  onChange={(e) => update("smtp_host", e.target.value)}
                  placeholder="smtp.gmail.com"
                />
                <Input
                  label="SMTP Port"
                  type="number"
                  value={form.smtp_port || ""}
                  onChange={(e) => update("smtp_port", parseInt(e.target.value))}
                  placeholder="587"
                />
              </div>
              <Input
                label="SMTP Username"
                value={form.smtp_user || ""}
                onChange={(e) => update("smtp_user", e.target.value)}
                placeholder="your@email.com"
              />
              <Input
                label="SMTP Password"
                type="password"
                value={form.smtp_password || ""}
                onChange={(e) => update("smtp_password", e.target.value)}
                placeholder="App password or SMTP password"
              />
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.smtp_tls ?? true}
                  onChange={(e) => update("smtp_tls", e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span className="text-sm text-slate-700">Use TLS/STARTTLS</span>
              </label>
            </CardContent>
          </Card>

          {/* Verification Settings */}
          <Card>
            <CardHeader><CardTitle>Verification Settings</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Consent Version</label>
                <input
                  value={form.consent_version || "1.0"}
                  onChange={(e) => update("consent_version", e.target.value)}
                  className="w-32 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Data Retention (days)</label>
                <input
                  type="number"
                  value={form.retention_days || 365}
                  onChange={(e) => update("retention_days", parseInt(e.target.value))}
                  className="w-32 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.auto_verify ?? true}
                  onChange={(e) => update("auto_verify", e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span className="text-sm text-slate-700">Auto-start verification after consent</span>
              </label>
            </CardContent>
          </Card>

          {/* LLM Settings */}
          <Card>
            <CardHeader><CardTitle>AI Provider Settings</CardTitle></CardHeader>
            <CardContent>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">LLM Provider</label>
                <select
                  value={form.llm_provider || "gemini"}
                  onChange={(e) => update("llm_provider", e.target.value)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
                >
                  <option value="gemini">Google Gemini Flash (Primary)</option>
                  <option value="openrouter">OpenRouter Free Models (Fallback)</option>
                </select>
                <p className="text-xs text-slate-400 mt-2">
                  Configure API keys via environment variables: GEMINI_API_KEY and OPENROUTER_API_KEY
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthGuard>
  );
}
