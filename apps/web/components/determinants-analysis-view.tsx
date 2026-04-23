"use client";

import { useEffect, useState } from "react";

import { fetchDeterminants, type ApiState } from "../lib/api";
import type { DeterminantsResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function DeterminantsAnalysisView() {
  const [region, setRegion] = useState("US");
  const [yearFrom, setYearFrom] = useState("2024");
  const [yearTo, setYearTo] = useState("2025");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<ApiState<DeterminantsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchDeterminants({
          region: region || undefined,
          yearFrom: yearFrom ? Number(yearFrom) : undefined,
          yearTo: yearTo ? Number(yearTo) : undefined,
          page: 1,
          pageSize: 20,
        });
        setState({ status: response.drivers.length > 0 ? "success" : "empty", data: response, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load determinants",
        });
      }
    }
    void load();
  }, [region, yearFrom, yearTo, reloadKey]);

  return (
    <AppShell
      title="Determinants Analysis"
      description="Driver-level aggregate analysis with explicit descriptive, associative, and causal-hypothesis labeling."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Driver Filters</h2>
              <p className="section-copy">Association outputs are not causal claims unless explicitly labeled.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="det-region">Region</label>
              <input id="det-region" value={region} onChange={(event) => setRegion(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="det-year-from">Year from</label>
              <input id="det-year-from" type="number" value={yearFrom} onChange={(event) => setYearFrom(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="det-year-to">Year to</label>
              <input id="det-year-to" type="number" value={yearTo} onChange={(event) => setYearTo(event.target.value)} />
            </div>
            <div className="field">
              <label>&nbsp;</label>
              <button className="data-state-button" type="button" onClick={() => setReloadKey((value) => value + 1)}>
                Refresh
              </button>
            </div>
          </div>
        </section>

        {renderDeterminants(state)}
      </main>
    </AppShell>
  );
}

function renderDeterminants(state: ApiState<DeterminantsResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading determinants" detail="Fetching grouped driver signals." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Determinants unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No data available yet" detail="No determinants returned for these filters." />;
  }

  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Methodology</h2>
            <p className="section-copy">{state.data.methodology.methodName} v{state.data.methodology.methodologyVersion}</p>
          </div>
          <span className="pill">{state.data.period}</span>
        </div>
        <div className="hero-points">
          <div className="hero-point">
            <strong>Assumptions</strong>
            <span className="muted">{state.data.methodology.assumptionsSummary}</span>
          </div>
          <div className="hero-point">
            <strong>Confidence</strong>
            <span className="muted">{state.data.methodology.confidenceSummary}</span>
          </div>
          <div className="hero-point">
            <strong>Causal Labeling Policy</strong>
            <span className="muted">{state.data.methodology.causalLabelingPolicy}</span>
          </div>
        </div>
      </section>

      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Determinant Drivers</h2>
            <p className="section-copy">Each row includes relationship type and uncertainty metadata.</p>
          </div>
          <span className="pill">{state.data.pagination.totalItems} drivers</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Factor</th>
                <th>Group</th>
                <th>Type</th>
                <th>Contribution</th>
                <th>Confidence</th>
                <th>Uncertainty</th>
              </tr>
            </thead>
            <tbody>
              {state.data.drivers.map((driver) => (
                <tr key={`${driver.factor}-${driver.category}`}>
                  <td>{driver.factor}</td>
                  <td>{driver.category}</td>
                  <td>{driver.relationshipType}</td>
                  <td>{driver.contributionScore.toFixed(1)}</td>
                  <td>{driver.confidence}</td>
                  <td>{driver.uncertaintyNote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
