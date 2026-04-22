type DataStateProps = {
  status: "loading" | "empty" | "error";
  title: string;
  detail: string;
  onRetry?: () => void;
};

const STATE_LABELS: Record<DataStateProps["status"], string> = {
  loading: "Loading",
  empty: "No data",
  error: "Error",
};

export function DataState({ status, title, detail, onRetry }: DataStateProps) {
  const isError = status === "error";
  const isLoading = status === "loading";

  return (
    <div className={`data-state${isError ? " data-state-error" : ""}${isLoading ? " data-state-loading" : ""}`}>
      <div>
        <div className="data-state-label">{STATE_LABELS[status]}</div>
        <strong>{title}</strong>
        <p>{detail}</p>
        {onRetry ? (
          <button type="button" className="data-state-button" onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </div>
    </div>
  );
}
