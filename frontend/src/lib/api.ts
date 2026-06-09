import axios, { AxiosInstance, AxiosError } from "axios";
import Cookies from "js-cookie";

const API_BASE = "";

const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api/v1/`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Attach token
api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → refresh
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as any;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = Cookies.get("refresh_token");
      if (refresh) {
        try {
          const res = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
            refresh_token: refresh,
          });
          const { access_token, refresh_token } = res.data;
          Cookies.set("access_token", access_token, { expires: 1 });
          Cookies.set("refresh_token", refresh_token, { expires: 7 });
          original.headers.Authorization = `Bearer ${access_token}`;
          return api(original);
        } catch {
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          if (typeof window !== "undefined") window.location.href = "/login";
        }
      } else {
        Cookies.remove("access_token");
        if (typeof window !== "undefined") window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: {
    company_name: string;
    website?: string;
    company_size?: string;
    industry?: string;
    first_admin_name: string;
    admin_email: string;
    password: string;
  }) => api.post("/auth/register", data),

  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", { refresh_token }),

  verifyEmail: (token: string) =>
    api.get(`/auth/verify-email?token=${token}`),
};

// ─── Dashboard ───────────────────────────────────────────────────────────────
export const dashboardApi = {
  getStats: () => api.get("/dashboard/stats"),
  getActivity: () => api.get("/dashboard/activity"),
};

// ─── Candidates ──────────────────────────────────────────────────────────────
export const candidatesApi = {
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get("/candidates/", { params }),

  get: (id: string) => api.get(`/candidates/${id}`),

  upload: (formData: FormData) =>
    api.post("candidates/", formData, {
      headers: { "Content-Type": undefined },
    }),

  delete: (id: string) => api.delete(`/candidates/${id}`),

  exportData: (id: string) => api.get(`/candidates/${id}/export`),

  downloadReport: (id: string) =>
    api.get(`/candidates/${id}/report`, { responseType: "blob" }),

  sendVerifications: (id: string) =>
    api.post(`/candidates/${id}/send-verifications`),

  updateEmploymentContact: (candidateId: string, recordId: string, email: string) =>
    api.patch(`/candidates/${candidateId}/employment/${recordId}/contact`, {
      contact_email: email,
    }),

  updateEducationContact: (candidateId: string, recordId: string, email: string) =>
    api.patch(`/candidates/${candidateId}/education/${recordId}/contact`, {
      contact_email: email,
    }),
};

// ─── Notifications ────────────────────────────────────────────────────────────
export const notificationsApi = {
  list: () => api.get("/notifications"),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
};

// ─── Settings ─────────────────────────────────────────────────────────────────
export const settingsApi = {
  get: () => api.get("/settings"),
  update: (data: Record<string, unknown>) => api.patch("/settings", data),
};

// ─── Users ────────────────────────────────────────────────────────────────────
export const usersApi = {
  list: () => api.get("/users"),
  create: (data: Record<string, unknown>) => api.post("/users", data),
};

// ─── Consent (public) ─────────────────────────────────────────────────────────
export const consentApi = {
  getInfo: (token: string) =>
    api.get(`/consent/${token}`),
  respond: (token: string, action: "accept" | "decline") =>
    api.post(`/consent/${token}/respond?action=${action}`),
};

export const verifyResponseApi = {
  getForm: (token: string) =>
    api.get(`/verify-response/${token}`),
  submit: (token: string, data: Record<string, unknown>) =>
    api.post(`/verify-response/${token}`, data),
};
