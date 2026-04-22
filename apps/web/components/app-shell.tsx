"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { fetchHealth, getEffectiveClientRole, type AppRole } from "../lib/api";

type AppShellProps = {
  title: string;
  description: string;
  children: ReactNode;
};

const ALL_ROLES: AppRole[] = [
  "admin",
  "analyst",
  "payer_aggregate_only",
  "trial_coordinator",
  "read_only_gov",
];
const RANKING_ROLES: AppRole[] = ["admin", "analyst", "trial_coordinator"];
const NAV_ITEMS = [
  { href: "/", label: "Dashboard", roles: ALL_ROLES },
  { href: "/disease-explorer", label: "Disease Explorer", roles: ALL_ROLES },
  { href: "/indication-prioritizer", label: "Indication Prioritizer", roles: RANKING_ROLES },
];

type HealthStatus = {
  state: "checking" | "ok" | "degraded";
  detail: string;
};

export function AppShell({ title, description, children }: AppShellProps) {
  const pathname = usePathname();
  const role = getEffectiveClientRole();
  const [health, setHealth] = useState<HealthStatus>({
    state: "checking",
    detail: "Checking API connectivity",
  });

  useEffect(() => {
    let mounted = true;

    async function checkHealth() {
      try {
        const response = await fetchHealth();
        if (!mounted) {
          return;
        }
        setHealth({
          state: response.status === "ok" ? "ok" : "degraded",
          detail: response.status === "ok" ? `API healthy (${response.environment})` : "API responded with degraded status",
        });
      } catch {
        if (!mounted) {
          return;
        }
        setHealth({
          state: "degraded",
          detail: "API unavailable. Live endpoint data may fail.",
        });
      }
    }

    void checkHealth();
    const intervalId = globalThis.setInterval(() => {
      void checkHealth();
    }, 30000);

    return () => {
      mounted = false;
      globalThis.clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="brand">
          <span className="brand-kicker">Healthcare Epidemiology</span>
          <h1 className="brand-title">{title}</h1>
          <p className="brand-copy">{description}</p>
        </div>
        <nav className="nav-tabs" aria-label="Primary">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            const isAllowed = role !== "unknown" && item.roles.includes(role);

            if (!isAllowed) {
              return (
                <span key={item.href} className="nav-tab nav-tab-disabled" aria-disabled="true">
                  {item.label}
                </span>
              );
            }

            return <Link key={item.href} href={item.href} className={`nav-tab${isActive ? " nav-tab-active" : ""}`}>{item.label}</Link>;
          })}
        </nav>
      </header>
      <section className={`status-banner status-banner-${health.state}`}>
        <span className="status-dot" aria-hidden="true" />
        <strong>Backend</strong>
        <span>{health.detail}</span>
        <span className="status-pill">Role: {role}</span>
      </section>
      {children}
    </div>
  );
}
