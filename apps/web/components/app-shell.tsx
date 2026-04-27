"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { fetchAuthMe, fetchDataQuality, fetchDebugSnapshot } from "../lib/api";
import type { AppRole } from "../lib/types";

type AppShellProps = {
  title: string;
  description: string;
  children: ReactNode;
};

type AppContextState = {
  role: AppRole | "unknown";
  tenantId: string;
  backendStatus: "ok" | "degraded" | "error";
  backendDetail: string;
  dqStatus: "ok" | "degraded";
  accessResolved: boolean;
};

const ALL_ROLES: Array<AppRole | "unknown"> = [
  "admin",
  "analyst",
  "read_only",
  "auditor",
  "operations",
  "payer_aggregate_only",
  "trial_coordinator",
  "read_only_gov",
  "unknown",
];

const ANALYST_ROLES: Array<AppRole | "unknown"> = [
  "admin",
  "analyst",
  "read_only",
  "auditor",
  "operations",
  "payer_aggregate_only",
  "trial_coordinator",
  "read_only_gov",
];

const DECISION_ROLES: Array<AppRole | "unknown"> = ["admin", "analyst", "operations", "trial_coordinator", "auditor"];

const ADMIN_ROLES: Array<AppRole | "unknown"> = ["admin", "operations", "auditor"];

const AUDIT_ROLES: Array<AppRole | "unknown"> = ["admin", "analyst", "read_only_gov"];

type NavItem = {
  href: string;
  label: string;
  roles: Array<AppRole | "unknown">;
  disabledReason?: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Command Center", roles: ALL_ROLES },
  { href: "/disease-explorer", label: "Disease Explorer", roles: ANALYST_ROLES },
  { href: "/incidence-prevalence", label: "Incidence & Prevalence", roles: ANALYST_ROLES },
  { href: "/determinants-analysis", label: "Determinants", roles: ANALYST_ROLES },
  { href: "/indication-prioritizer", label: "Indication Prioritizer", roles: DECISION_ROLES },
  { href: "/simulation-lab", label: "Simulation Lab", roles: DECISION_ROLES },
  { href: "/compare-scenarios", label: "Compare Scenarios", roles: DECISION_ROLES },
  { href: "/data-quality-center", label: "Data Quality", roles: ANALYST_ROLES },
  {
    href: "/ingestion-run-center",
    label: "Ingestion Runs",
    roles: ADMIN_ROLES,
    disabledReason: "Requires admin, operations, or auditor role.",
  },
  { href: "/audit-viewer", label: "Audit Activity", roles: AUDIT_ROLES },
  { href: "/methodology-center", label: "Methodology", roles: ALL_ROLES },
  { href: "/health-diagnostics", label: "Health & Runtime", roles: ALL_ROLES },
  {
    href: "/admin-tenant-settings",
    label: "Admin & Tenant",
    roles: ADMIN_ROLES,
    disabledReason: "Requires admin, operations, or auditor role.",
  },
];

export function AppShell({ title, description, children }: AppShellProps) {
  const pathname = usePathname();
  const [context, setContext] = useState<AppContextState>({
    role: "unknown",
    tenantId: "unknown",
    backendStatus: "error",
    backendDetail: "Checking backend",
    dqStatus: "ok",
    accessResolved: false,
  });

  useEffect(() => {
    let mounted = true;
    async function loadContext() {
      try {
        const [debug, auth, dq] = await Promise.all([
          fetchDebugSnapshot(),
          fetchAuthMe(),
          fetchDataQuality({ page: 1, pageSize: 5 }),
        ]);
        if (!mounted) return;
        setContext({
          role: auth.role ?? "unknown",
          tenantId: auth.tenantId ?? "unknown",
          backendStatus: debug.backend.status === "ok" ? "ok" : "degraded",
          backendDetail: debug.backend.detail,
          dqStatus: dq.status,
          accessResolved: true,
        });
      } catch (error) {
        if (!mounted) return;
        setContext((previous) => ({
          ...previous,
          backendStatus: "error",
          backendDetail: error instanceof Error ? error.message : "Backend unavailable",
          accessResolved: false,
        }));
      }
    }

    void loadContext();
    const intervalId = setInterval(() => {
      void loadContext();
    }, 20000);
    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const breadcrumbs = useMemo(() => {
    const parts = pathname.split("/").filter(Boolean);
    if (parts.length === 0) return ["Command Center"];
    return parts.map((part) => part.replace(/-/g, " ").replace(/\b\w/g, (token) => token.toUpperCase()));
  }, [pathname]);

  return (
    <div className="os-shell">
      <aside className="os-nav">
        <div className="os-brand">
          <span className="os-brand-kicker">EpiOS</span>
          <h1 className="os-brand-title">Enterprise Intelligence OS</h1>
          <p className="os-brand-copy">Aggregate-first epidemiology and strategy operations.</p>
        </div>
        <nav className="os-nav-links" aria-label="Platform modules">
          {NAV_ITEMS.map((item) => {
            const enabled = !context.accessResolved || item.roles.includes(context.role);
            const active = pathname === item.href;
            if (!enabled) {
              return (
                <span
                  key={item.href}
                  className="os-nav-link os-nav-link-disabled"
                  aria-disabled="true"
                  title={item.disabledReason ?? "Unavailable for your current role."}
                >
                  {item.label}
                </span>
              );
            }

            const checkingAccess = !context.accessResolved;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`os-nav-link${active ? " os-nav-link-active" : ""}${checkingAccess ? " os-nav-link-pending" : ""}`}
                title={checkingAccess ? "Access is being resolved; availability may update." : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="os-main">
        <header className="os-header">
          <div>
            <div className="os-breadcrumbs">{breadcrumbs.join(" / ")}</div>
            <h2 className="os-page-title">{title}</h2>
            <p className="os-page-copy">{description}</p>
          </div>
          <div className="os-context-grid">
            <ContextBadge label="Tenant" value={context.tenantId} tone="neutral" />
            <ContextBadge label="Role" value={context.role} tone="neutral" />
            <ContextBadge label="Backend" value={context.backendStatus} tone={context.backendStatus === "ok" ? "ok" : "warn"} />
            <ContextBadge label="Data Quality" value={context.dqStatus} tone={context.dqStatus === "ok" ? "ok" : "warn"} />
          </div>
        </header>
        <section className={`os-status-banner os-status-${context.backendStatus === "ok" ? "ok" : "warn"}`}>
          <strong>Runtime</strong>
          <span>{context.backendDetail}</span>
        </section>
        <main className="os-content">{children}</main>
      </div>
    </div>
  );
}

function ContextBadge({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" | "neutral" }) {
  return (
    <div className={`os-context-badge os-context-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
