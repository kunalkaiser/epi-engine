"use client";

import { useEffect, useState } from "react";

import { fetchDebugSnapshot, fetchHealth, fetchReady, fetchRuntimeDebug, type ApiState } from "../lib/api";
import type { DebugSnapshot, HealthResponse, ReadyResponse, RuntimeDebugResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

type DiagnosticsPayload = {
  debug: DebugSnapshot;
  health: HealthResponse;
  ready: ReadyResponse;
  runtime: RuntimeDebugResponse;
};

export function HealthDiagnosticsView() {
  const [state, setState] = useState<ApiState<DiagnosticsPayload>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function load() {
      setState({ status: "loading", data: null, error: null });
      try {
        const [debug, health, ready, runtime] = await Promise.all([
          fetchDebugSnapshot(),
          fetchHealth(),
          fetchReady(),
          fetchRuntimeDebug(),
        ]);
        setState({ status: "success", data: { debug, health, ready, runtime }, error: null });
      } catch (error) {
        setState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Diagnostics request failed",
        });
      }
    }
    void load();
  }, []);

  return (
    <AppShell
      title="Health, Runtime, and Diagnostics"
      description="End-to-end platform diagnostics without secret exposure."
    >
      <main className="page-grid">{renderDiagnostics(state)}</main>
    </AppShell>
  );
}

function renderDiagnostics(state: ApiState<DiagnosticsPayload>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading diagnostics" detail="Checking frontend, backend, readiness, and runtime flags." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Diagnostics unavailable" detail={state.error} />;
  }
  if (!state.data) {
    return <DataState status="empty" title="No diagnostics payload" detail="Diagnostics response was empty." />;
  }

  return (
    <>
      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Runtime Snapshot</h2>
            <p className="section-copy">Safe environment and readiness diagnostics.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Check</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Frontend</td>
                <td>{state.data.debug.frontend.status}</td>
              </tr>
              <tr>
                <td>Backend</td>
                <td>{state.data.debug.backend.status}</td>
              </tr>
              <tr>
                <td>Auth</td>
                <td>{state.data.debug.auth.status}</td>
              </tr>
              <tr>
                <td>Ready</td>
                <td>{state.data.ready.status}</td>
              </tr>
              <tr>
                <td>Environment</td>
                <td>{state.data.runtime.environment}</td>
              </tr>
              <tr>
                <td>ClickHouse URL Present</td>
                <td>{state.data.runtime.clickhouseUrlPresent ? "yes" : "no"}</td>
              </tr>
              <tr>
                <td>Auth Configured</td>
                <td>{state.data.runtime.authConfigured ? "yes" : "no"}</td>
              </tr>
              <tr>
                <td>Metrics Enabled</td>
                <td>{state.data.runtime.metricsEnabled ? "yes" : "no"}</td>
              </tr>
              <tr>
                <td>Trace Header</td>
                <td>{state.data.runtime.traceHeaderName}</td>
              </tr>
              <tr>
                <td>Queued Simulation Runs</td>
                <td>{state.data.runtime.queuedSimulationRuns ?? "unavailable"}</td>
              </tr>
              <tr>
                <td>Pilot Mode</td>
                <td>{state.data.runtime.pilotModeEnabled ? `enabled (${state.data.runtime.pilotModeLabel ?? "pilot"})` : "disabled"}</td>
              </tr>
              <tr>
                <td>Auth Token Source</td>
                <td>{state.data.debug.auth.tokenSource}</td>
              </tr>
              <tr>
                <td>Auth Header Attached</td>
                <td>{state.data.debug.auth.attached ? "yes" : "no"}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Readiness Dependencies</h2>
            <p className="section-copy">Dependency checks from `/ready`.</p>
          </div>
        </div>
        <div className="hero-points">
          {state.data.ready.dependencies.map((dependency) => (
            <div className="hero-point" key={dependency.name}>
              <strong>{dependency.name}</strong>
              <span className="muted">
                {dependency.status}: {dependency.detail}
              </span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
