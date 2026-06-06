"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import { dashboardApi, notificationsApi } from "@/lib/api";
import { StatCard, Card, CardHeader, CardTitle, CardContent, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { Users, Clock, Activity, CheckCircle, AlertTriangle, Bell } from "lucide-react";
import { formatDateTime, statusConfig } from "@/lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import Link from "next/link";

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e", moderate: "#f59e0b", high: "#f97316", critical: "#ef4444",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      dashboardApi.getStats(),
      dashboardApi.getActivity(),
      notificationsApi.list(),
    ]).then(([statsRes, activityRes, notifRes]) => {
      setStats(statsRes.data);
      setActivity(activityRes.data);
      setNotifications(notifRes.data?.filter((n: any) => !n.is_read).slice(0, 5));
    }).finally(() => setLoading(false));
  }, []);

  const statusChartData = stats
    ? Object.entries(stats.charts?.verification_status || {}).map(([key, val]) => ({
        name: statusConfig[key as keyof typeof statusConfig]?.label || key,
        value: val as number,
      })).filter((d) => d.value > 0)
    : [];

  const riskChartData = stats
    ? Object.entries(stats.charts?.risk_distribution || {}).map(([key, val]) => ({
        name: key.charAt(0).toUpperCase() + key.slice(1),
        value: val as number,
        color: RISK_COLORS[key] || "#94a3b8",
      })).filter((d) => d.value > 0)
    : [];

  if (loading) {
    return (
      <AuthGuard>
        <div className="flex items-center justify-center h-64">
          <Spinner />
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">
            Good {new Date().getHours() < 12 ? "morning" : "afternoon"},{" "}
            {user?.full_name?.split(" ")[0] || "there"} 👋
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">Here's your verification overview</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <StatCard title="Total Candidates" value={stats?.stats?.total_candidates ?? 0} icon={<Users className="w-5 h-5" />} color="bg-sky-50 text-sky-600" />
          <StatCard title="Pending Consent" value={stats?.stats?.pending_consents ?? 0} icon={<Clock className="w-5 h-5" />} color="bg-yellow-50 text-yellow-600" />
          <StatCard title="Active Checks" value={stats?.stats?.active_verifications ?? 0} icon={<Activity className="w-5 h-5" />} color="bg-purple-50 text-purple-600" />
          <StatCard title="Completed" value={stats?.stats?.completed_verifications ?? 0} icon={<CheckCircle className="w-5 h-5" />} color="bg-green-50 text-green-600" />
          <StatCard title="High Risk" value={stats?.stats?.high_risk_candidates ?? 0} icon={<AlertTriangle className="w-5 h-5" />} color="bg-red-50 text-red-600" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Status Chart */}
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Verification Status Distribution</CardTitle></CardHeader>
            <CardContent>
              {statusChartData.length === 0 ? (
                <div className="h-40 flex items-center justify-center text-slate-400 text-sm">No data yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={statusChartData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                    <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Risk Chart */}
          <Card>
            <CardHeader><CardTitle>Risk Distribution</CardTitle></CardHeader>
            <CardContent>
              {riskChartData.length === 0 ? (
                <div className="h-40 flex items-center justify-center text-slate-400 text-sm">No risk data yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={riskChartData} cx="50%" cy="45%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                      {riskChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Activity */}
          <Card>
            <CardHeader><CardTitle>Recent Activity</CardTitle></CardHeader>
            <CardContent className="p-0">
              {activity.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-sm">No activity yet</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {activity.slice(0, 8).map((log: any) => (
                    <div key={log.id} className="px-6 py-3 flex items-center justify-between">
                      <div>
                        <p className="text-sm text-slate-700 font-medium capitalize">
                          {log.action.replace(/_/g, " ")}
                        </p>
                        <p className="text-xs text-slate-400">{log.entity_type} · {log.entity_id?.slice(0, 8)}...</p>
                      </div>
                      <span className="text-xs text-slate-400">{formatDateTime(log.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Notifications</CardTitle>
              <Bell className="w-4 h-4 text-slate-400" />
            </CardHeader>
            <CardContent className="p-0">
              {notifications.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-sm">All caught up!</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {notifications.map((n: any) => (
                    <div key={n.id} className="px-6 py-3">
                      <p className="text-sm font-medium text-slate-800">{n.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{n.message}</p>
                      {n.entity_id && (
                        <Link href={`/candidates/${n.entity_id}`} className="text-xs text-sky-500 hover:text-sky-600 mt-1 inline-block">
                          View →
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthGuard>
  );
}
