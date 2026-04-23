"use client";

import { useEffect, useState } from "react";

import { fetchIngestionRuns, type ApiState } from "../lib/api";
import type { IngestionRunsResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function IngestionRunCenterView() {
  const [sourceSystem, setSourceSystem] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<ApiState<IngestionRunsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchIngestionRuns({
          sourceSystem: sourceSystem || undefined,
          status: statusFilter || undefined,
          page: 1,
          pageSize: 25,
        });
        setState({ status: response.items.length > 0 ? "success" : "empty", data: response, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load ingestion runs",
        });
      }
    }
    void load();
  }, [sourceSystem, statusFilter, reloadKey]);

  return (
    <AppShell
      title="Ingestion Run Center"
      description="Operational run history with source, status, and record-level pipeline counters."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Run Filters</h2>
              <p className="section-copy">Admin and operations roles can inspect pipeline history and freshness.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="ing-source">Source system</label>
              <input id="ing-source" value={sourceSystem} onChange={(event) => setSourceSystem(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ing-status">Status</label>
              <select id="ing-status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All</option>
                <option value="queued">queued</option>
                <option value="running">running</option>
                <option value="succeeded">succeeded</option>
                <option value="failed">failed</option>
                <option value="cancelled">cancelled</option>
              </select>
            </div>
            <div className="field">
              <label>&nbsp;</label>
              <button className="data-state-button" type="button" onClick={() => setReloadKey((value) => value + 1)}>
                Refresh
              </button>
            </div>
          </div>
        </section>
        {renderIngestionState(state)}
      </main>
    </AppShell>
  );
}

function renderIngestionState(state: ApiState<IngestionRunsResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading ingestion runs" detail="Fetching latest persisted run records." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Ingestion runs unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No ingestion runs found" detail="No runs match current filters." />;
  }
  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Run History</h2>
          <p className="section-copy">Counts are aggregate process telemetry only.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Dataset</th>
              <th>Source</th>
              <th>Status</th>
              <th>Processed</th>
              <th>Inserted</th>
              <th>Rejected</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={item.runId}>
                <td>{item.runId}</td>
                <td>{item.datasetName}</td>
                <td>{item.sourceSystem}</td>
                <td>{item.status}</td>
                <td>{item.recordsProcessed.toLocaleString()}</td>
                <td>{item.recordsInserted.toLocaleString()}</td>
                <td>{item.recordsRejected.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
