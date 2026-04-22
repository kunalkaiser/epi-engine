"use client";

import { useEffect, useState } from "react";

import { fetchTopIndications, getEffectiveClientRole, isEmptyResponse, type ApiState } from "../lib/api";
import type { TopIndicationsResponse } from "../lib/types";
import { AppShell } from "./app-shell";
import { ChartBars } from "./chart-bars";
import { DataState } from "./data-state";

const REGION_OPTIONS = ["", "US", "CA"];

export function IndicationPrioritizerView() {
  const role = getEffectiveClientRole();
  const canAccessPrioritizer = role === "admin" || role === "analyst" || role === "trial_coordinator";
  const [reloadKey, setReloadKey] = useState(0);
  const [region, setRegion] = useState("US");
  const [limit, setLimit] = useState("3");
  const [pageSize, setPageSize] = useState("5");
  const [state, setState] = useState<ApiState<TopIndicationsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    if (!canAccessPrioritizer) {
      return;
    }

    async function loadRankings() {
      setState({ status: "loading", data: null, error: null });
      try {
        const response = await fetchTopIndications({
          region: region || undefined,
          limit: Number(limit),
          page: 1,
          pageSize: Number(pageSize),
        });

        setState({
          status: isEmptyResponse(response) ? "empty" : "success",
          data: response,
          error: null,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown API error";
        setState({ status: "error", data: null, error: message });
      }
    }

    void loadRankings();
  }, [region, limit, pageSize, reloadKey, canAccessPrioritizer]);

  const retry = () => {
    setReloadKey((value) => value + 1);
  };

  return (
    <AppShell
      title="Indication Prioritizer"
      description="Rank candidate indications using the API scoring feed, with transparent component scores and lightweight visual comparison."
    >
      <main className="page-grid">
        {!canAccessPrioritizer ? (
          <DataState
            status="error"
            title="Indication prioritization is restricted"
            detail={`Role ${role} cannot access ranking endpoints. Aggregate trend views remain available.`}
          />
        ) : null}
        {canAccessPrioritizer ? (
          <>
            <section className="panel">
              <div className="section-heading">
                <div>
                  <h2 className="section-title">Filters</h2>
                  <p className="section-copy">Tune the ranking slice by region and result count.</p>
                </div>
              </div>
              <div className="filter-row">
                <div className="field">
                  <label htmlFor="region">Region suffix</label>
                  <select id="region" value={region} onChange={(event) => setRegion(event.target.value)}>
                    {REGION_OPTIONS.map((option) => (
                      <option key={option || "all"} value={option}>
                        {option || "All suffixes"}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="limit">Top limit</label>
                  <input id="limit" type="number" value={limit} onChange={(event) => setLimit(event.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="page-size">Page size</label>
                  <input
                    id="page-size"
                    type="number"
                    value={pageSize}
                    onChange={(event) => setPageSize(event.target.value)}
                  />
                </div>
              </div>
            </section>

            {renderPrioritizerBody(state, retry)}
          </>
        ) : null}
      </main>
    </AppShell>
  );
}

function renderPrioritizerBody(state: ApiState<TopIndicationsResponse>, onRetry: () => void) {
  if (state.status === "loading") {
    return <DataState status="loading" title="Loading rankings" detail="Fetching top indications from the API." />;
  }
  if (state.status === "error") {
    return <DataState status="error" title="Ranking request failed" detail={state.error} onRetry={onRetry} />;
  }
  if (state.status === "empty" || !state.data) {
    return <DataState status="empty" title="No indications returned" detail="Try changing the region suffix or limit." />;
  }

  return (
    <>
      <section className="two-column">
        <ChartBars
          title="Composite Score"
          subtitle="Basic chart comparing the current ranking results."
          data={state.data.items.map((item) => ({
            label: item.indicationName,
            value: item.totalScore,
            displayValue: item.totalScore.toFixed(1),
          }))}
        />
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Ranking Summary</h2>
              <p className="section-copy">Quick interpretation of the current prioritization slice.</p>
            </div>
          </div>
          <div className="hero-points">
            {state.data.items.map((item, index) => (
              <div className="hero-point" key={item.indicationId}>
                <strong>
                  #{index + 1} {item.indicationName}
                </strong>
                <span className="muted">
                  Total {item.totalScore.toFixed(1)} with incidence {item.incidenceScore.toFixed(1)} and unmet need{" "}
                  {item.unmetNeedScore.toFixed(1)}.
                </span>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="table-panel">
        <div className="section-heading">
          <div>
            <h2 className="section-title">Scoring Table</h2>
            <p className="section-copy">Transparent component scores for each returned indication.</p>
          </div>
          <span className="pill">Page {state.data.pagination.page}</span>
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
    </>
  );
}
