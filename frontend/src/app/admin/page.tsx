"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { usersApi } from "@/lib/api";
import { Card, CardContent, Badge, Button, Input, PageHeader } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/utils";
import { UserPlus, Shield, X, CheckCircle } from "lucide-react";

export default function AdminPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "recruiter" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isAdmin = user?.role === "org_admin" || user?.role === "super_admin";

  useEffect(() => {
    if (isAdmin) {
      usersApi.list().then((res) => setUsers(res.data)).catch(() => {});
    }
  }, [isAdmin]);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await usersApi.create(form);
      const res = await usersApi.list();
      setUsers(res.data);
      setShowForm(false);
      setForm({ email: "", full_name: "", password: "", role: "recruiter" });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const roleColors: Record<string, string> = {
    super_admin: "bg-red-100 text-red-700",
    org_admin: "bg-purple-100 text-purple-700",
    recruiter: "bg-blue-100 text-blue-700",
    reviewer: "bg-teal-100 text-teal-700",
  };

  if (!isAdmin) {
    return (
      <AuthGuard>
        <div className="p-6 text-center">
          <Shield className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">Admin access required</p>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="p-6 max-w-4xl mx-auto">
        <PageHeader
          title="Admin"
          description="Manage team members and access"
          action={
            <Button onClick={() => setShowForm(true)}>
              <UserPlus className="w-4 h-4" />
              Add User
            </Button>
          }
        />

        {/* Add User Form */}
        {showForm && (
          <Card className="mb-6 border-sky-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">Add Team Member</h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <CardContent>
              {error && (
                <div className="mb-4 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{error}</div>
              )}
              <form onSubmit={createUser} className="grid grid-cols-2 gap-4">
                <Input
                  label="Full Name"
                  value={form.full_name}
                  onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                  required
                />
                <Input
                  label="Email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  required
                />
                <Input
                  label="Password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Role</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
                  >
                    <option value="recruiter">Recruiter</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="org_admin">Org Admin</option>
                  </select>
                </div>
                <div className="col-span-2 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" loading={saving}>Create User</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Users Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100">
                  {["Name", "Email", "Role", "Status", "Last Login", "Joined"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-sky-100 flex items-center justify-center text-sky-600 text-xs font-semibold">
                          {u.full_name?.[0]?.toUpperCase() || "U"}
                        </div>
                        <span className="text-sm font-medium text-slate-900">{u.full_name}</span>
                        {u.id === user?.id && <Badge className="bg-sky-100 text-sky-700">You</Badge>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">{u.email}</td>
                    <td className="px-4 py-3">
                      <Badge className={roleColors[u.role] || "bg-slate-100 text-slate-600"}>
                        {u.role.replace(/_/g, " ")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-green-400" : "bg-red-400"}`} />
                        <span className="text-xs text-slate-500">{u.is_active ? "Active" : "Inactive"}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{u.last_login ? formatDateTime(u.last_login) : "Never"}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{formatDateTime(u.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AuthGuard>
  );
}
