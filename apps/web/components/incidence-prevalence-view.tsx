"use client";

import { useEffect, useState } from "react";

import { fetchIncidence, fetchMortality, fetchPrevalence, isEmptyResponse, type ApiState } from "../lib/api";
import type { IncidenceResponse, MortalityResponse, PrevalenceResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { ChartBars } from "./chart-bars";
import { DataState } from "./data-state";

export function IncidencePrevalenceView() {
  const [region, setRegion] = useState("");
  const [yearFrom, setYearFrom] = useState("2024");
  const [yearTo, setYearTo] = useState("2025");
  const [reloadKey, setReloadKey] = useState(0);
  const [incidence, setIncidence] = useState<ApiState<IncidenceResponse>>({ status: "loading", data: null, error: null });
  const [prevalence, setPrevalence] = useState<ApiState<PrevalenceResponse>>({ status: "loading", data: null, error: null });
  const [mortality, setMortality] = useState<ApiState<MortalityResponse>>({ status: "loading", data: null, error: null });

  useEffect(() => {
    async function load() {
      setIncidence({ status: "loading", data: null, error: null });
      setPrevalence({ status: "loading", data: null, error: null });
      setMortality({ status: "loading", data: null, error: null });
      const filters = {
        region: region || undefined,
        yearFrom: yearFrom ? Number(yearFrom) : undefined,
        yearTo: yearTo ? Number(yearTo) : undefined,
        page: 1,
        pageSize: 8,
      };
      try {
        const [incidenceData, prevalenceData, mortalityData] = await Promise.all([
          fetchIncidence(filters),
          fetchPrevalence(filters),
          fetchMortality(filters),
        ]);
        setIncidence({ status: isEmptyResponse(incidenceData) ? "empty" : "success", data: incidenceData, error: null });
        setPrevalence({ status: isEmptyResponse(prevalenceData) ? "empty" : "success", data: prevalenceData, error: null });
        setMortality({ status: isEmptyResponse(mortalityData) ? "empty" : "success", data: mortalityData, error: null });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown API error";
        setIncidence({ status: "error", data: null, error: message });
        setPrevalence({ status: "error", data: null, error: message });
        setMortality({ status: "error", data: null, error: message });
      }
    }
    void load();
  }, [region, yearFrom, yearTo, reloadKey]);

  return (
    <AppShell
      title="Incidence and Prevalence Explorer"
      description="Aggregate burden trends with incidence, prevalence, and mortality views by region and time."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Analysis Filters</h2>
              <p className="section-copy">All results are aggregate-only and tenant scoped.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="ip-region">Region</label>
              <input id="ip-region" value={region} onChange={(event) => setRegion(event.target.value)} placeholder="US or US-CA" />
            </div>
            <div className="field">
              <label htmlFor="ip-year-from">Year from</label>
              <input id="ip-year-from" type="number" value={yearFrom} onChange={(event) => setYearFrom(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ip-year-to">Year to</label>
              <input id="ip-year-to" type="number" value={yearTo} onChange={(event) => setYearTo(event.target.value)} />
            </div>
            <div className="field">
              <label>&nbsp;</label>
              <button className="data-state-button" type="button" onClick={() => setReloadKey((value) => value + 1)}>
                Refresh
              </button>
            </div>
          </div>
        </section>

        <section className="two-column">
          {renderTrendState("Incidence Per 100k", "Latest incidence slice.", incidence, (item) => ({
            label: `${item.diseaseName} ${item.year}`,
            value: item.incidencePer100k,
            displayValue: item.incidencePer100k.toFixed(1),
          }))}
          {renderTrendState("Prevalence Per 100k", "Latest prevalence slice.", prevalence, (item) => ({
            label: `${item.diseaseName} ${item.year}`,
            value: item.prevalencePer100k,
            displayValue: item.prevalencePer100k.toFixed(1),
          }))}
        </section>

        {renderTrendState("Mortality Per 100k", "Latest mortality slice.", mortality, (item) => ({
          label: `${item.diseaseName} ${item.year}`,
          value: item.mortalityPer100k,
          displayValue: item.mortalityPer100k.toFixed(1),
        }))}
      </main>
    </AppShell>
  );
}

function renderTrendState<T extends { items: any[] }>(
  title: string,
  subtitle: string,
  state: ApiState<T>,
  mapper: (item: any) => { label: string; value: number; displayValue: string },
) {
  if (state.status === "loading") {
    return <DataState status="loading" title={`Loading ${title.toLowerCase()}`} detail="Fetching live aggregate data." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title={`${title} unavailable`} detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No data available yet" detail="Connected successfully but no rows match these filters." />;
  }
  return <ChartBars title={title} subtitle={subtitle} data={state.data.items.map(mapper)} />;
}
