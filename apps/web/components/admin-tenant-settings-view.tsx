"use client";

import { useEffect, useState } from "react";

import { fetchAuthMe, fetchDataQuality, fetchIngestionRuns, type ApiState } from "../lib/api";
import type { AuthMeResponse, DataQualityResponse, IngestionRunsResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

type AdminPayload = {
  auth: AuthMeResponse;
  dataQuality: DataQualityResponse;
  ingestion: IngestionRunsResponse;
};

export function AdminTenantSettingsView() {
  const [state, setState] = useState<ApiState<AdminPayload>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const [auth, dataQuality, ingestion] = await Promise.all([
          fetchAuthMe(),
          fetchDataQuality({ page: 1, pageSize: 5 }),
          fetchIngestionRuns({ page: 1, pageSize: 5 }),
        ]);
        setState({ status: "success", data: { auth, dataQuality, ingestion }, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load admin settings",
        });
      }
    }
    void load();
  }, []);

  return (
    <AppShell
      title="Admin and Tenant Settings"
      description="Role, tenant context, and operational summaries for controlled administrative workflows."
    >
      <main className="page-grid">{renderAdminState(state)}</main>
    </AppShell>
  );
}

function renderAdminState(state: ApiState<AdminPayload>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading tenant settings" detail="Resolving role and tenant-scoped operations summary." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Admin settings unavailable" detail={state.error} />;
  }
  if (!state.data) {
    return <DataState status="empty" title="No admin payload" detail="Admin payload was empty." />;
  }

  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Tenant Context</h2>
            <p className="section-copy">Resolved from authenticated server-side claims.</p>
          </div>
        </div>
        <div className="hero-points">
          <div className="hero-point">
            <strong>Tenant</strong>
            <span className="muted">{state.data.auth.tenantId}</span>
          </div>
          <div className="hero-point">
            <strong>Role</strong>
            <span className="muted">{state.data.auth.role}</span>
          </div>
          <div className="hero-point">
            <strong>Subject</strong>
            <span className="muted">{state.data.auth.subject}</span>
          </div>
        </div>
      </section>
      <section className="two-column">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Data Quality Summary</h2>
              <p className="section-copy">Latest quality rows visible to this tenant.</p>
            </div>
          </div>
          <p className="stat-value">{state.data.dataQuality.pagination.totalItems}</p>
        </section>
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Ingestion Summary</h2>
              <p className="section-copy">Latest ingestion runs visible to this tenant.</p>
            </div>
          </div>
          <p className="stat-value">{state.data.ingestion.pagination.totalItems}</p>
        </section>
      </section>
    </>
  );
}
