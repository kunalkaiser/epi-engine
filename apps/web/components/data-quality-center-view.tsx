"use client";

import { useEffect, useState } from "react";

import { fetchDataQuality, type ApiState } from "../lib/api";
import type { DataQualityResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function DataQualityCenterView() {
  const [domain, setDomain] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<ApiState<DataQualityResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchDataQuality({
          domain: domain || undefined,
          status: statusFilter || undefined,
          page: 1,
          pageSize: 25,
        });
        setState({ status: response.items.length > 0 ? "success" : "empty", data: response, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load data quality results",
        });
      }
    }
    void load();
  }, [domain, statusFilter, reloadKey]);

  return (
    <AppShell
      title="Data Quality Center"
      description="Operational view of quality runs, severities, rule versions, and aggregate trust signals."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Quality Filters</h2>
              <p className="section-copy">Filter by domain and status for trend and triage workflows.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="dq-domain">Domain</label>
              <input id="dq-domain" value={domain} onChange={(event) => setDomain(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="dq-status">Status</label>
              <select id="dq-status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All</option>
                <option value="pass">pass</option>
                <option value="warn">warn</option>
                <option value="fail">fail</option>
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
        {renderQualityState(state)}
      </main>
    </AppShell>
  );
}

function renderQualityState(state: ApiState<DataQualityResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading quality results" detail="Fetching latest quality checks." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Data quality unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No data quality rows" detail="No quality checks found for the current filters." />;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Quality Runs</h2>
          <p className="section-copy">Status: {state.data.status}. Generated: {new Date(state.data.generatedAt).toLocaleString()}</p>
        </div>
        <span className="pill">{state.data.pagination.totalItems} rows</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Domain</th>
              <th>Check Type</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Rules Version</th>
              <th>Measured At</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={item.resultId}>
                <td>{item.domain}</td>
                <td>{item.checkType}</td>
                <td>{item.severity}</td>
                <td>{item.status}</td>
                <td>{item.rulesVersion}</td>
                <td>{new Date(item.measuredAt).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
