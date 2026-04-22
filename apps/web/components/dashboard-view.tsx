"use client";

import { useEffect, useState } from "react";

import { AppShell } from "./app-shell";
import { ChartBars } from "./chart-bars";
import { DataState } from "./data-state";
import { fetchDiseases, fetchIncidence, fetchTopIndications, isEmptyResponse, type ApiState } from "../lib/api";
import type { DiseasesResponse, IncidenceResponse, TopIndicationsResponse } from "../lib/types";

export function DashboardView() {
  const [reloadKey, setReloadKey] = useState(0);
  const [diseasesState, setDiseasesState] = useState<ApiState<DiseasesResponse>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [incidenceState, setIncidenceState] = useState<ApiState<IncidenceResponse>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [indicationsState, setIndicationsState] = useState<ApiState<TopIndicationsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function loadDashboard() {
      setDiseasesState({ status: "loading", data: null, error: null });
      setIncidenceState({ status: "loading", data: null, error: null });
      setIndicationsState({ status: "loading", data: null, error: null });

      try {
        const [diseases, incidence, indications] = await Promise.all([
          fetchDiseases(1, 6),
          fetchIncidence({ page: 1, pageSize: 6 }),
          fetchTopIndications({ page: 1, pageSize: 5, limit: 5 }),
        ]);

        setDiseasesState({
          status: isEmptyResponse(diseases) ? "empty" : "success",
          data: diseases,
          error: null,
        });
        setIncidenceState({
          status: isEmptyResponse(incidence) ? "empty" : "success",
          data: incidence,
          error: null,
        });
        setIndicationsState({
          status: isEmptyResponse(indications) ? "empty" : "success",
          data: indications,
          error: null,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown API error";
        setDiseasesState({ status: "error", data: null, error: message });
        setIncidenceState({ status: "error", data: null, error: message });
        setIndicationsState({ status: "error", data: null, error: message });
      }
    }

    void loadDashboard();
  }, [reloadKey]);

  const retry = () => {
    setReloadKey((value) => value + 1);
  };

  const topDisease = incidenceState.data?.items[0];
  const topIndication = indicationsState.data?.items[0];

  return (
    <AppShell
      title="EPI Engine"
      description="A fast, aggregate-first workspace for disease landscape review, trend analysis, and indication prioritization."
    >
      <main className="page-grid">
        <section className="hero-card">
          <div>
            <span className="eyebrow">Decision Snapshot</span>
            <h2 className="section-title">Start from disease burden, then move directly into prioritization.</h2>
            <p className="section-copy">
              The dashboard surfaces the current disease catalog, recent incidence movement, and the top-ranked indications
              from the API so a team can orient itself before deeper analysis.
            </p>
            <div className="hero-points">
              <div className="hero-point">
                <strong>Aggregate by design</strong>
                <span className="muted">No patient-level drill-down, only cohort-safe trend and scoring views.</span>
              </div>
              <div className="hero-point">
                <strong>Direct API connection</strong>
                <span className="muted">Every panel reads the current FastAPI endpoints instead of mock frontend-only state.</span>
              </div>
            </div>
          </div>
          <div className="hero-chart-card">
            <div>
              <span className="eyebrow">Current Lead</span>
              <h3 className="section-title" style={{ marginTop: 8 }}>
                {topIndication?.indicationName ?? "Waiting for API data"}
              </h3>
              <p className="section-copy">
                {topIndication
                  ? `Top score ${topIndication.totalScore.toFixed(1)} based on the current prioritization feed.`
                  : "The prioritization card will populate once the API responds."}
              </p>
            </div>
            <div className="status-note">
              {topDisease
                ? `${topDisease.diseaseName} has the highest recent incidence in the loaded dashboard slice.`
                : "Recent disease burden will appear here after loading."}
            </div>
          </div>
        </section>

        <section className="panel-grid">
          <article className="stat-card">
            <div className="stat-label">Tracked Diseases</div>
            <p className="stat-value">{diseasesState.data?.pagination.totalItems ?? "..."}</p>
            <p className="stat-meta">Distinct diseases available from the API catalog.</p>
          </article>
          <article className="stat-card">
            <div className="stat-label">Latest Incidence View</div>
            <p className="stat-value">
              {topDisease ? topDisease.incidencePer100k.toFixed(1) : "..."}
            </p>
            <p className="stat-meta">Incidence per 100k for the first item in the latest sorted result set.</p>
          </article>
          <article className="stat-card">
            <div className="stat-label">Top Indication Score</div>
            <p className="stat-value">{topIndication ? topIndication.totalScore.toFixed(1) : "..."}</p>
            <p className="stat-meta">Composite prioritization score from the ranking endpoint.</p>
          </article>
        </section>

        <section className="two-column">
          {renderDashboardDiseasePanel(diseasesState, retry)}
          {renderDashboardIncidencePanel(incidenceState, retry)}
        </section>

        {renderTopIndications(indicationsState, retry)}
      </main>
    </AppShell>
  );
}

function renderDashboardDiseasePanel(state: ApiState<DiseasesResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading disease catalog" detail="Fetching disease metadata from the API." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Disease catalog unavailable" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No diseases returned" detail="The API returned an empty disease catalog." />;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Disease Catalog</h2>
          <p className="section-copy">Current disease entries available for explorer workflows.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Disease</th>
              <th>Regions</th>
              <th>Year Range</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={item.diseaseId}>
                <td>{item.diseaseName}</td>
                <td>{item.regions.join(", ")}</td>
                <td>
                  {item.yearMin}-{item.yearMax}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function renderDashboardIncidencePanel(state: ApiState<IncidenceResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading incidence trends" detail="Fetching the latest incidence slice." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Incidence unavailable" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No incidence data" detail="The API returned no incidence rows." />;
  }

  return (
    <ChartBars
      title="Latest Incidence Per 100k"
      subtitle="Quick burden comparison from the current response payload."
      data={state.data.items.map((item) => ({
        label: `${item.diseaseName} ${item.regionCode}`,
        value: item.incidencePer100k,
        displayValue: item.incidencePer100k.toFixed(1),
      }))}
    />
  );
}

function renderTopIndications(state: ApiState<TopIndicationsResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading indication rankings" detail="Pulling prioritization scores from the API." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Indications unavailable" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No indication scores" detail="The prioritization endpoint returned no rows." />;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Top Indications</h2>
          <p className="section-copy">Highest-ranked indications from the prioritization endpoint.</p>
        </div>
        <span className="pill">Top {state.data.items.length}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Indication</th>
              <th>Total</th>
              <th>Incidence</th>
              <th>Unmet Need</th>
              <th>Market Size</th>
              <th>Competition</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={item.indicationId}>
                <td>{item.indicationName}</td>
                <td>{item.totalScore.toFixed(1)}</td>
                <td>{item.incidenceScore.toFixed(1)}</td>
                <td>{item.unmetNeedScore.toFixed(1)}</td>
                <td>{item.marketSizeScore.toFixed(1)}</td>
                <td>{item.competitionScore.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
