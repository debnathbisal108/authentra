"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import Cookies from "js-cookie";
import { authApi } from "@/lib/api";
import { useRouter } from "next/navigation";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  isAuthenticated: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (token) {
      // Decode JWT payload (no verification needed client-side)
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload.exp * 1000 > Date.now()) {
          setUser({
            id: payload.sub,
            email: payload.email || "",
            full_name: payload.name || "",
            role: payload.role || "recruiter",
            organization_id: payload.org || "",
          });
        } else {
          Cookies.remove("access_token");
        }
      } catch {
        Cookies.remove("access_token");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    const { access_token, refresh_token } = res.data;
    Cookies.set("access_token", access_token, { expires: 1 });
    Cookies.set("refresh_token", refresh_token, { expires: 7 });

    // Decode user from token
    const payload = JSON.parse(atob(access_token.split(".")[1]));
    setUser({
      id: payload.sub,
      email: email,
      full_name: payload.name || email.split("@")[0],
      role: payload.role || "recruiter",
      organization_id: payload.org || "",
    });
    router.push("/dashboard");
  };

  const logout = () => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
