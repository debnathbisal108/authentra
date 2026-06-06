import { cn } from "@/lib/utils";
import { ReactNode, InputHTMLAttributes, ButtonHTMLAttributes, forwardRef, SelectHTMLAttributes } from "react";

// ─── Badge ────────────────────────────────────────────────────────────────────
interface BadgeProps { children: ReactNode; className?: string; }
export function Badge({ children, className }: BadgeProps) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", className)}>
      {children}
    </span>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("bg-white rounded-xl border border-slate-200 shadow-sm", className)}>{children}</div>;
}
export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("px-6 py-4 border-b border-slate-100", className)}>{children}</div>;
}
export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h3 className={cn("text-sm font-semibold text-slate-900", className)}>{children}</h3>;
}
export function CardContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("px-6 py-4", className)}>{children}</div>;
}

// ─── Button ───────────────────────────────────────────────────────────────────
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive" | "secondary";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, className, variant = "default", size = "md", loading, disabled, ...props }, ref) => {
    const base = "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed";
    const variants = {
      default: "bg-sky-500 text-white hover:bg-sky-600 active:bg-sky-700",
      outline: "border border-slate-200 text-slate-700 bg-white hover:bg-slate-50",
      ghost: "text-slate-600 hover:bg-slate-100",
      destructive: "bg-red-500 text-white hover:bg-red-600",
      secondary: "bg-slate-100 text-slate-700 hover:bg-slate-200",
    };
    const sizes = { sm: "px-3 py-1.5 text-xs gap-1.5", md: "px-4 py-2 text-sm gap-2", lg: "px-5 py-2.5 text-sm gap-2" };
    return (
      <button ref={ref} className={cn(base, variants[variant], sizes[size], className)} disabled={disabled || loading} {...props}>
        {loading && <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

// ─── Input ────────────────────────────────────────────────────────────────────
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }>(
  ({ className, label, error, id, ...props }, ref) => (
    <div className="space-y-1.5">
      {label && <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>}
      <input
        ref={ref}
        id={id}
        className={cn(
          "w-full px-3 py-2 text-sm border rounded-lg bg-white text-slate-900 placeholder:text-slate-400",
          "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500",
          "disabled:bg-slate-50 disabled:text-slate-500",
          error ? "border-red-300 focus:ring-red-500 focus:border-red-500" : "border-slate-300",
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
);
Input.displayName = "Input";

// ─── Select ───────────────────────────────────────────────────────────────────
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & { label?: string }>(
  ({ className, label, id, children, ...props }, ref) => (
    <div className="space-y-1.5">
      {label && <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>}
      <select
        ref={ref}
        id={id}
        className={cn(
          "w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white text-slate-900",
          "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500",
          className
        )}
        {...props}
      >
        {children}
      </select>
    </div>
  )
);
Select.displayName = "Select";

// ─── Stat Card ────────────────────────────────────────────────────────────────
interface StatCardProps { title: string; value: number | string; icon: ReactNode; color?: string; }
export function StatCard({ title, value, icon, color = "bg-sky-50 text-sky-600" }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-5">
        <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0", color)}>
          {icon}
        </div>
        <div>
          <p className="text-xs text-slate-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon: ReactNode; title: string; description?: string; action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-12 h-12 text-slate-300 mb-4">{icon}</div>
      <h3 className="text-sm font-semibold text-slate-700 mb-1">{title}</h3>
      {description && <p className="text-sm text-slate-500 max-w-sm mb-4">{description}</p>}
      {action}
    </div>
  );
}

// ─── Loading Spinner ──────────────────────────────────────────────────────────
export function Spinner({ className }: { className?: string }) {
  return <div className={cn("w-5 h-5 border-2 border-sky-500 border-t-transparent rounded-full animate-spin", className)} />;
}

// ─── Page Header ──────────────────────────────────────────────────────────────
export function PageHeader({ title, description, action }: {
  title: string; description?: string; action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
        {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
