"use client";

import { useEffect, useState } from "react";

import { fetchMethodology, type ApiState } from "../lib/api";
import type { MethodologyResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function MethodologyCenterView() {
  const [state, setState] = useState<ApiState<MethodologyResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchMethodology();
        setState({ status: "success", data: response, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load methodology",
        });
      }
    }
    void load();
  }, []);

  return (
    <AppShell
      title="Methodology and Explainability Center"
      description="Transparent methods, assumptions, and model versioning across scoring, determinants, and simulation."
    >
      <main className="page-grid">
        {renderMethodology(state)}
      </main>
    </AppShell>
  );
}

function renderMethodology(state: ApiState<MethodologyResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading methodology" detail="Fetching model and policy metadata." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Methodology unavailable" detail={state.error} />;
  }
  if (!state.data) {
    return <DataState status="empty" title="No methodology metadata" detail="Methodology payload is empty." />;
  }
  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Methodology Version</h2>
            <p className="section-copy">Generated at {new Date(state.data.generatedAt).toLocaleString()}</p>
          </div>
          <span className="pill">{state.data.modelVersion}</span>
        </div>
        <div className="hero-points">
          <div className="hero-point">
            <strong>Scoring</strong>
            <span className="muted">{readSummaryField(state.data.scoring, "explainability", "No scoring summary provided.")}</span>
          </div>
          <div className="hero-point">
            <strong>Determinants</strong>
            <span className="muted">{readSummaryField(state.data.determinants, "guardrail", "No determinants guardrail provided.")}</span>
          </div>
          <div className="hero-point">
            <strong>Simulation</strong>
            <span className="muted">{readSummaryField(state.data.simulation, "reproducibility", "No simulation reproducibility summary provided.")}</span>
          </div>
        </div>
      </section>
      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Scoring Methodology</h2>
            <p className="section-copy">Classification and limits are explicit to avoid over-interpretation.</p>
          </div>
        </div>
        <div className="hero-points">
          {renderObjectEntries(state.data.scoring)}
        </div>
      </section>
      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Determinants Methodology</h2>
            <p className="section-copy">Descriptive, associative, and causal-hypothesis outputs are separated.</p>
          </div>
        </div>
        <div className="hero-points">
          {renderObjectEntries(state.data.determinants)}
        </div>
      </section>
      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Simulation Methodology</h2>
            <p className="section-copy">Scenario results are projections with assumptions and uncertainty, not causal proof.</p>
          </div>
        </div>
        <div className="hero-points">
          {renderObjectEntries(state.data.simulation)}
        </div>
      </section>
    </>
  );
}

function readSummaryField(record: Record<string, unknown>, field: string, fallback: string): string {
  const value = record[field];
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return fallback;
}

function renderObjectEntries(record: Record<string, unknown>) {
  return Object.entries(record).map(([key, value]) => (
    <div className="hero-point" key={key}>
      <strong>{key.replace(/_/g, " ")}</strong>
      <span className="muted">{formatValue(value)}</span>
    </div>
  ));
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join("; ");
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "n/a";
}
