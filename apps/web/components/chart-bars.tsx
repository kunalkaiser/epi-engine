type ChartDatum = {
  label: string;
  value: number;
  displayValue?: string;
};

type ChartBarsProps = {
  title: string;
  subtitle?: string;
  data: ChartDatum[];
};

export function ChartBars({ title, subtitle, data }: ChartBarsProps) {
  const maxValue = Math.max(...data.map((item) => item.value), 1);

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2 className="section-title">{title}</h2>
          {subtitle ? <p className="section-copy">{subtitle}</p> : null}
        </div>
      </div>
      <div className="chart">
        {data.map((item) => (
          <div key={item.label} className="chart-row">
            <strong>{item.label}</strong>
            <div className="chart-track" aria-hidden="true">
              <div
                className="chart-bar"
                style={{ width: `${Math.max((item.value / maxValue) * 100, 4)}%` }}
              />
            </div>
            <span className="muted">{item.displayValue ?? item.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
