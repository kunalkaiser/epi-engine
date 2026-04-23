"use client";

import { useEffect, useState } from "react";

import { compareSimulationRuns, fetchSimulationRuns, type ApiState } from "../lib/api";
import type { SimulationComparisonResponse, SimulationRunSummary } from "../lib/types";
import { AppShell } from "./app-shell";
import { DataState } from "./data-state";

export function CompareScenariosView() {
  const [runsState, setRunsState] = useState<ApiState<{ items: SimulationRunSummary[] }>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [compareState, setCompareState] = useState<ApiState<SimulationComparisonResponse>>({
    status: "empty",
    data: null,
    error: null,
  });

  useEffect(() => {
    async function loadRuns() {
      setRunsState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchSimulationRuns({ page: 1, pageSize: 30 });
        setRunsState({ status: response.items.length > 0 ? "success" : "empty", data: { items: response.items }, error: null });
      } catch (error) {
        setRunsState({
          status: "error",
          data: null,
          error: error instanceof Error ? error.message : "Unable to load simulation runs",
        });
      }
    }
    void loadRuns();
  }, []);

  async function runComparison() {
    if (selectedRunIds.length < 2) {
      setCompareState({
        status: "error",
        data: null,
        error: "Select at least two runs for comparison.",
      });
      return;
    }
    setCompareState({ status: "loading", data: null, error: null });
    try {
      const response = await compareSimulationRuns(selectedRunIds);
      setCompareState({ status: response.scoreDeltas.length > 0 ? "success" : "empty", data: response, error: null });
    } catch (error) {
      setCompareState({
        status: "error",
        data: null,
        error: error instanceof Error ? error.message : "Comparison failed",
      });
    }
  }

  return (
    <AppShell
      title="Compare Scenarios"
      description="Compare simulation runs side-by-side with assumption and score deltas."
    >
      <main className="page-grid">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Select Runs</h2>
              <p className="section-copy">Choose 2-5 simulation runs from tenant-scoped history.</p>
            </div>
            <button className="data-state-button" type="button" onClick={() => void runComparison()}>
              Compare
            </button>
          </div>
          {renderRunSelection(runsState, selectedRunIds, setSelectedRunIds)}
        </section>
        {renderComparison(compareState)}
      </main>
    </AppShell>
  );
}

function renderRunSelection(
  state: ApiState<{ items: SimulationRunSummary[] }>,
  selectedRunIds: string[],
  setSelectedRunIds: (runIds: string[]) => void,
) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading runs" detail="Fetching completed and in-flight simulations." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Runs unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No runs available" detail="Create simulation runs before comparing scenarios." />;
  }

  function toggle(runId: string) {
    const exists = selectedRunIds.includes(runId);
    if (exists) {
      setSelectedRunIds(selectedRunIds.filter((item) => item !== runId));
      return;
    }
    if (selectedRunIds.length >= 5) return;
    setSelectedRunIds([...selectedRunIds, runId]);
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Select</th>
            <th>Run ID</th>
            <th>Scenario</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {state.data.items.map((run) => (
            <tr key={run.runId}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedRunIds.includes(run.runId)}
                  onChange={() => toggle(run.runId)}
                />
              </td>
              <td>{run.runId}</td>
              <td>{run.scenarioType}</td>
              <td>{run.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderComparison(state: ApiState<SimulationComparisonResponse>) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Comparing scenarios" detail="Computing assumption and score deltas." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Comparison unavailable" detail={state.error} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No comparison output yet" detail="Pick runs and start comparison." />;
  }

  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Assumption Deltas</h2>
            <p className="section-copy">Detected assumption key differences across compared runs.</p>
          </div>
        </div>
        <div className="hero-points">
          {Object.entries(state.data.assumptionDeltas).map(([runId, deltas]) => (
            <div className="hero-point" key={runId}>
              <strong>{runId}</strong>
              <span className="muted">{deltas.length > 0 ? deltas.join(", ") : "No assumption delta keys."}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Score Deltas</h2>
            <p className="section-copy">Biggest movers by spread across selected runs.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Indication</th>
                <th>Min</th>
                <th>Max</th>
                <th>Spread</th>
              </tr>
            </thead>
            <tbody>
              {state.data.scoreDeltas.map((item) => (
                <tr key={item.indicationId}>
                  <td>{item.indicationName}</td>
                  <td>{item.minScore.toFixed(1)}</td>
                  <td>{item.maxScore.toFixed(1)}</td>
                  <td>{item.scoreSpread.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
