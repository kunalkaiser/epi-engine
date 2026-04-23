"use client";

import { useEffect, useState } from "react";

import { fetchIncidence, fetchPrevalence, isEmptyResponse, type ApiState } from "../lib/api";
import type { IncidenceResponse, PrevalenceResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { ChartBars } from "./chart-bars";
import { DataState } from "./data-state";

const REGION_OPTIONS = ["", "US", "US-CA"];

export function DiseaseExplorerView() {
  const [reloadKey, setReloadKey] = useState(0);
  const [region, setRegion] = useState("");
  const [yearFrom, setYearFrom] = useState("2024");
  const [yearTo, setYearTo] = useState("2025");
  const [incidenceState, setIncidenceState] = useState<ApiState<IncidenceResponse>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [prevalenceState, setPrevalenceState] = useState<ApiState<PrevalenceResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function loadExplorer() {
      setIncidenceState({ status: "loading", data: null, error: null });
      setPrevalenceState({ status: "loading", data: null, error: null });

      const filters = {
        region: region || undefined,
        yearFrom: yearFrom ? Number(yearFrom) : undefined,
        yearTo: yearTo ? Number(yearTo) : undefined,
        page: 1,
        pageSize: 20,
      };

      try {
        const [incidence, prevalence] = await Promise.all([fetchIncidence(filters), fetchPrevalence(filters)]);

        setIncidenceState({
          status: isEmptyResponse(incidence) ? "empty" : "success",
          data: incidence,
          error: null,
        });
        setPrevalenceState({
          status: isEmptyResponse(prevalence) ? "empty" : "success",
          data: prevalence,
          error: null,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown API error";
        setIncidenceState({ status: "error", data: null, error: message });
        setPrevalenceState({ status: "error", data: null, error: message });
      }
    }

    void loadExplorer();
  }, [region, yearFrom, yearTo, reloadKey]);

  const retry = () => {
    setReloadKey((value) => value + 1);
  };

  return (
    <AppShell
      title="Disease Explorer"
      description="Compare aggregate incidence and prevalence by region and year using the current API responses."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Filters</h2>
              <p className="section-copy">Adjust region and time bounds to narrow the explorer views.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="region">Region</label>
              <select id="region" value={region} onChange={(event) => setRegion(event.target.value)}>
                {REGION_OPTIONS.map((option) => (
                  <option key={option || "all"} value={option}>
                    {option || "All regions"}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="year-from">Year from</label>
              <input
                id="year-from"
                type="number"
                value={yearFrom}
                onChange={(event) => setYearFrom(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="year-to">Year to</label>
              <input
                id="year-to"
                type="number"
                value={yearTo}
                onChange={(event) => setYearTo(event.target.value)}
              />
            </div>
          </div>
        </section>

        <section className="two-column">
          {renderIncidenceChart(incidenceState, retry)}
          {renderPrevalenceChart(prevalenceState, retry)}
        </section>

        <section className="two-column">
          {renderIncidenceTable(incidenceState)}
          {renderPrevalenceTable(prevalenceState)}
        </section>
      </main>
    </AppShell>
  );
}

function renderIncidenceChart(state: ApiState<IncidenceResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading incidence" detail="Fetching incidence rows for the current filters." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Incidence request failed" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return (
      <DataState
        status="empty"
        title="No data available yet"
        detail="Connected to the API, but there are no incidence rows for the selected filters."
      />
    );
  }

  return (
    <ChartBars
      title="Incidence Per 100k"
      subtitle="Basic chart derived from the filtered incidence table."
      data={state.data.items.map((item) => ({
        label: `${item.diseaseName} ${item.year}`,
        value: item.incidencePer100k,
        displayValue: item.incidencePer100k.toFixed(1),
      }))}
    />
  );
}

function renderPrevalenceChart(state: ApiState<PrevalenceResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading prevalence" detail="Fetching prevalence rows for the current filters." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Prevalence request failed" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return (
      <DataState
        status="empty"
        title="No data available yet"
        detail="Connected to the API, but there are no prevalence rows for the selected filters."
      />
    );
  }

  return (
    <ChartBars
      title="Prevalence Per 100k"
      subtitle="Basic chart derived from the filtered prevalence table."
      data={state.data.items.map((item) => ({
        label: `${item.diseaseName} ${item.year}`,
        value: item.prevalencePer100k,
        displayValue: item.prevalencePer100k.toFixed(1),
      }))}
    />
  );
}

function renderIncidenceTable(state: ApiState<IncidenceResponse>) {
  if (state.status !== "success" || !state.data) {
    return null;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Incidence Table</h2>
          <p className="section-copy">Filtered disease incidence rows from the API.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Disease</th>
              <th>Region</th>
              <th>Year</th>
              <th>Cases</th>
              <th>Per 100k</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={`${item.diseaseId}-${item.regionCode}-${item.year}`}>
                <td>{item.diseaseName}</td>
                <td>{item.regionCode}</td>
                <td>{item.year}</td>
                <td>{item.incidentCases.toLocaleString()}</td>
                <td>{item.incidencePer100k.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function renderPrevalenceTable(state: ApiState<PrevalenceResponse>) {
  if (state.status !== "success" || !state.data) {
    return null;
  }

  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Prevalence Table</h2>
          <p className="section-copy">Filtered disease prevalence rows from the API.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Disease</th>
              <th>Region</th>
              <th>Year</th>
              <th>Cases</th>
              <th>Per 100k</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={`${item.diseaseId}-${item.regionCode}-${item.year}`}>
                <td>{item.diseaseName}</td>
                <td>{item.regionCode}</td>
                <td>{item.year}</td>
                <td>{item.prevalentCases.toLocaleString()}</td>
                <td>{item.prevalencePer100k.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
