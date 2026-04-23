"use client";

import { useEffect, useMemo, useState } from "react";

import {
  cancelSimulationRun,
  createSimulationRun,
  fetchSimulationResult,
  fetchSimulationRuns,
  type ApiState,
} from "../lib/api";
import type { SimulationResultResponse, SimulationRunSummary } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

const SCENARIO_TYPES = [
  "subpopulation_targeting",
  "regional_expansion",
  "trial_feasibility",
  "weighting_change",
] as const;

export function SimulationLabView() {
  const [scenarioType, setScenarioType] = useState<(typeof SCENARIO_TYPES)[number]>("subpopulation_targeting");
  const [region, setRegion] = useState("US");
  const [limit, setLimit] = useState("10");
  const [assumptions, setAssumptions] = useState('{"uptake_delta": 0.1}');
  const [runsState, setRunsState] = useState<ApiState<{ items: SimulationRunSummary[] }>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [resultState, setResultState] = useState<ApiState<SimulationResultResponse>>({
    status: "empty",
    data: null,
    error: null,
  });
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function loadRuns() {
    setRunsState({ status: "loading", data: null, error: null });
    try {
      const response = await fetchSimulationRuns({ page: 1, pageSize: 20 });
      setRunsState({ status: response.items.length > 0 ? "success" : "empty", data: { items: response.items }, error: null });
      if (!selectedRunId && response.items[0]?.runId) {
        setSelectedRunId(response.items[0].runId);
      }
    } catch (error) {
      setRunsState({
        status: "error",
        data: null,
        error: error instanceof Error ? error.message : "Unable to load simulation runs",
      });
    }
  }

  useEffect(() => {
    void loadRuns();
    const timer = globalThis.setInterval(() => {
      void loadRuns();
    }, 8000);
    return () => globalThis.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      setResultState({ status: "empty", data: null, error: null });
      return;
    }
    let active = true;
    async function loadResult() {
      setResultState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchSimulationResult(selectedRunId);
        if (!active) return;
        setResultState({ status: response.items.length > 0 ? "success" : "empty", data: response, error: null });
      } catch (error) {
        if (!active) return;
        setResultState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load simulation result",
        });
      }
    }
    void loadResult();
    return () => {
      active = false;
    };
  }, [selectedRunId]);

  const selectedRun = useMemo(
    () => runsState.data?.items.find((run) => run.runId === selectedRunId) ?? null,
    [runsState.data, selectedRunId],
  );

  async function onCreateRun() {
    setSubmitError(null);
    let parsedAssumptions: Record<string, unknown> = {};
    try {
      parsedAssumptions = assumptions.trim() ? (JSON.parse(assumptions) as Record<string, unknown>) : {};
    } catch {
      setSubmitError("Assumptions must be valid JSON.");
      return;
    }

    try {
      const response = await createSimulationRun({
        scenarioType,
        region: region || undefined,
        limit: Number(limit) || 10,
        assumptions: parsedAssumptions,
      });
      setSelectedRunId(response.runId);
      await loadRuns();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Simulation submission failed");
    }
  }

  async function onCancel(runId: string) {
    try {
      await cancelSimulationRun(runId);
      await loadRuns();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Unable to cancel simulation run");
    }
  }

  return (
    <AppShell
      title="Simulation Lab"
      description="Queue scenario runs, track status transitions, and review explainable aggregate results."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Create Simulation Run</h2>
              <p className="section-copy">Submission is asynchronous. API returns immediately with a persistent run ID.</p>
            </div>
          </div>
          <div className="filter-row">
            <div className="field">
              <label htmlFor="sim-scenario">Scenario type</label>
              <select id="sim-scenario" value={scenarioType} onChange={(event) => setScenarioType(event.target.value as (typeof SCENARIO_TYPES)[number])}>
                {SCENARIO_TYPES.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="sim-region">Region</label>
              <input id="sim-region" value={region} onChange={(event) => setRegion(event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="sim-limit">Limit</label>
              <input id="sim-limit" type="number" value={limit} onChange={(event) => setLimit(event.target.value)} />
            </div>
            <div className="field field-wide">
              <label htmlFor="sim-assumptions">Assumptions JSON</label>
              <textarea id="sim-assumptions" value={assumptions} onChange={(event) => setAssumptions(event.target.value)} rows={4} />
            </div>
            <div className="field">
              <label>&nbsp;</label>
              <button className="data-state-button" type="button" onClick={() => void onCreateRun()}>
                Submit Run
              </button>
            </div>
          </div>
          {submitError ? <p className="error-note">{submitError}</p> : null}
        </section>

        <section className="two-column">
          {renderRunsPanel(runsState, selectedRunId, setSelectedRunId, onCancel)}
          {renderResultPanel(resultState, selectedRun)}
        </section>
      </main>
    </AppShell>
  );
}

function renderRunsPanel(
  state: ApiState<{ items: SimulationRunSummary[] }>,
  selectedRunId: string,
  onSelect: (runId: string) => void,
  onCancel: (runId: string) => void,
) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading simulation runs" detail="Checking queue and run history." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Simulation runs unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No simulation runs yet" detail="Submit a run to initialize tenant-scoped history." />;
  }
  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Run History</h2>
          <p className="section-copy">Queued, running, succeeded, failed, and cancelled lifecycle states.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Scenario</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((run) => (
              <tr key={run.runId} className={run.runId === selectedRunId ? "row-active" : ""}>
                <td>
                  <button className="link-button" type="button" onClick={() => onSelect(run.runId)}>
                    {run.runId}
                  </button>
                </td>
                <td>{run.scenarioType}</td>
                <td>{run.status}</td>
                <td>
                  {run.attemptCount}/{run.maxAttempts}
                </td>
                <td>
                  {(run.status === "queued" || run.status === "running") ? (
                    <button className="data-state-button" type="button" onClick={() => onCancel(run.runId)}>
                      Cancel
                    </button>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function renderResultPanel(state: ApiState<SimulationResultResponse>, selectedRun: SimulationRunSummary | null) {
  if (!selectedRun) {
    return <DataState status="empty" title="Select a run" detail="Choose a run from history to load detailed results." />;
  }
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading simulation result" detail="Fetching run outputs and trace metadata." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Simulation result unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="Run has no result rows yet" detail="Worker may still be processing or produced an empty output." />;
  }
  return (
    <section className="table-panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">Run Result</h2>
          <p className="section-copy">{selectedRun.methodology.methodName} v{selectedRun.methodology.methodologyVersion}</p>
        </div>
        <span className="pill">{selectedRun.status}</span>
      </div>
      <div className="hero-points" style={{ marginTop: 0, marginBottom: 16 }}>
        <div className="hero-point">
          <strong>Assumptions</strong>
          <span className="muted">{JSON.stringify(state.data.assumptions)}</span>
        </div>
        <div className="hero-point">
          <strong>Confidence</strong>
          <span className="muted">{selectedRun.methodology.confidenceSummary}</span>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Indication</th>
              <th>Baseline</th>
              <th>Simulated</th>
              <th>Delta</th>
              <th>Uncertainty</th>
              <th>Trace</th>
            </tr>
          </thead>
          <tbody>
            {state.data.items.map((item) => (
              <tr key={item.traceId}>
                <td>{item.indicationName}</td>
                <td>{item.baselineScore.toFixed(1)}</td>
                <td>{item.simulatedScore.toFixed(1)}</td>
                <td>{item.scoreDelta.toFixed(1)}</td>
                <td>
                  {item.uncertaintyLow.toFixed(1)} - {item.uncertaintyHigh.toFixed(1)}
                </td>
                <td>{item.traceId}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
