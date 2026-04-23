"use client";

import { useEffect, useState } from "react";

import { fetchAuditEvents, type ApiState } from "../lib/api";
import type { AuditEventsResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function AuditViewerView() {
  const [page, setPage] = useState(1);
  const [state, setState] = useState<ApiState<AuditEventsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchAuditEvents({ page, pageSize: 25 });
        setState({ status: response.items.length > 0 ? "success" : "empty", data: response, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load audit events",
        });
      }
    }
    void load();
  }, [page]);

  return (
    <AppShell
      title="Audit and Activity Viewer"
      description="Tenant-scoped event visibility for access, simulation, and operational activity."
    >
      <main className="page-grid">
        {renderAuditState(state)}
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Pagination</h2>
              <p className="section-copy">Use page navigation for chronological event review.</p>
            </div>
          </div>
          <div className="filter-row">
            <button className="data-state-button" type="button" onClick={() => setPage((value) => Math.max(1, value - 1))}>
              Previous
            </button>
            <span className="pill">Page {page}</span>
            <button className="data-state-button" type="button" onClick={() => setPage((value) => value + 1)}>
              Next
            </button>
          </div>
        </section>
      </main>
    </AppShell>
  );
}

function renderAuditState(state: ApiState<AuditEventsResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading activity" detail="Fetching persisted audit records." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Audit feed unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No audit events found" detail="No events exist for this page." />;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Audit Events</h2>
          <p className="section-copy">Operational and decision-trace events from API services.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Event Name</th>
              <th>Payload</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item, index) => (
              <tr key={`${item.event_name}-${index}`}>
                <td>{item.event_name}</td>
                <td>{JSON.stringify(item.payload)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
