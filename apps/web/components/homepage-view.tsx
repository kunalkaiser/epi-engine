import Link from "next/link";

const trustItems = ["Methodology visibility", "Evidence-labeled outputs", "Healthcare-native analytics"];

const frictionPoints = [
  {
    title: "Data remains siloed",
    marker: "01",
    tone: "data",
    note: "Clinical, epidemiology, and outcomes context stay separated across teams and systems.",
  },
  {
    title: "Evidence takes too long",
    marker: "02",
    tone: "timing",
    note: "Analysts spend too much time moving from intake to governed evidence review.",
  },
  {
    title: "Methods are hard to explain",
    marker: "03",
    tone: "methods",
    note: "Decision-makers need methodology context attached, not buried in analyst handoffs.",
  },
  {
    title: "Signals are over-interpreted",
    marker: "04",
    tone: "signals",
    note: "Teams need confidence, labels, and quality context before signals travel to decisions.",
  },
];

const workflowSteps = [
  { title: "Ask", status: "Intake ready" },
  { title: "Define cohort", status: "Criteria governed" },
  { title: "Review signals", status: "Signal set checked" },
  { title: "Label evidence", status: "Evidence typed" },
  { title: "Review quality", status: "Quality OK" },
  { title: "Export decision summary", status: "Export ready" },
];

const architectureLayers = [
  {
    label: "Layer 1",
    title: "Data Foundation",
    modules: ["Clinical data", "Epidemiology", "Outcomes", "Utilization"],
  },
  {
    label: "Layer 2",
    title: "Evidence Graph",
    modules: ["Cohorts", "Determinants", "Methods", "Quality", "Labels"],
  },
  {
    label: "Layer 3",
    title: "Intelligence Modules",
    modules: ["Command Center", "Disease Explorer", "Determinants Analysis", "Simulation Lab"],
  },
  {
    label: "Layer 4",
    title: "Decision Outputs",
    modules: ["Evidence summaries", "Prioritization", "Executive reports"],
  },
];

const solutions = [
  {
    title: "Life Sciences",
    marker: "Evidence strategy",
    items: ["HEOR and RWE", "Medical affairs", "Clinical strategy", "Market access", "Commercial planning"],
  },
  {
    title: "Health Systems",
    marker: "Operational intelligence",
    items: ["Population health", "Quality improvement", "Pharmacy strategy", "Service line planning", "Operational analytics"],
  },
];

const disciplineLabels = [
  {
    title: "Descriptive",
    tone: "descriptive",
    description: "Summarizes what is happening across populations, utilization, and outcomes.",
  },
  {
    title: "Associative",
    tone: "associative",
    description: "Highlights linked patterns that guide further investigation and prioritization.",
  },
  {
    title: "Causal hypothesis",
    tone: "hypothesis",
    description: "Frames directional evidence carefully so teams know where stronger proof is needed.",
  },
  {
    title: "Quality context",
    tone: "quality",
    description: "Keeps confidence, completeness, and governance visible before outputs move forward.",
  },
];

const networkFlowSteps = ["Question", "Cohort", "Signals", "Evidence", "Decision"];
const networkSupportCards = ["Methods", "Quality", "Labels", "Determinants"];

const heroNodes = [
  { title: "Question", x: 300, y: 170 },
  { title: "Cohort", x: 688, y: 170 },
  { title: "Signals", x: 244, y: 294 },
  { title: "Methods", x: 744, y: 294 },
  { title: "Quality", x: 340, y: 414 },
  { title: "Decision", x: 648, y: 414 },
];

const heroMetrics = [
  { title: "Cohorts", value: "12.4M", className: "map-metric" },
  { title: "Signals", value: "17", className: "map-metric" },
  { title: "Confidence", value: "92%", className: "map-metric map-metric-confidence" },
];

export function HomepageView() {
  return (
    <main className="home-page">
      <header className="site-header">
        <div className="home-shell site-header-inner">
          <Link href="/" className="site-logo" aria-label="EPI Engine home">
            EPI Engine
          </Link>
          <nav className="site-nav" aria-label="Primary">
            <a href="#why">Why</a>
            <a href="#evidence-network">Evidence Network</a>
            <a href="#evidence-agent">Evidence Agent</a>
            <a href="#platform">Platform</a>
            <a href="#solutions">Solutions</a>
            <a href="#demo" className="site-nav-button">
              Request demo
            </a>
          </nav>
        </div>
      </header>

      <section className="hero-section">
        <div className="home-shell hero-layout">
          <div className="hero-copy">
            <span className="section-eyebrow">Healthcare Evidence Intelligence</span>
            <h1>Turn healthcare data into evidence teams can trust.</h1>
            <p className="hero-subheadline">
              EPI Engine helps healthcare and life sciences teams move from fragmented clinical, epidemiology, and
              outcomes data to transparent, evidence-ready decisions.
            </p>
            <div className="hero-why-box" id="why">
              <span className="hero-why-label">Why EPI Engine</span>
              <p>
                Healthcare has more data than ever. But evidence is still slow to generate, hard to explain, and
                disconnected from decisions. EPI Engine creates a governed evidence layer from question to action.
              </p>
            </div>
            <div className="hero-actions">
              <a href="#demo" className="button button-primary">
                Request a demo
              </a>
              <a href="#evidence-network" className="button button-secondary">
                Explore the evidence layer
              </a>
            </div>
            <div className="hero-proof-points">
              {trustItems.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </div>
          <div className="hero-visual-wrap">
            <EvidenceIntelligenceMap />
          </div>
        </div>
      </section>

      <section className="trust-band">
        <div className="home-shell trust-band-inner">
          <span>Designed for governed evidence operations across healthcare and life sciences teams.</span>
        </div>
      </section>

      <section className="section problem-section">
        <div className="home-shell problem-grid">
          <div className="section-copy-block">
            <span className="section-eyebrow">Problem Narrative</span>
            <h2>Healthcare data is abundant. Trusted evidence is still hard to generate.</h2>
            <p>
              Clinical, operational, epidemiologic, and outcomes data are often fragmented across systems. Teams need
              evidence that is timely, reproducible, explainable, and appropriate for the decision at hand.
            </p>
          </div>
          <div className="friction-stack">
            {frictionPoints.map((point) => (
              <article key={point.title} className={`friction-item friction-item-${point.tone}`}>
                <div className="friction-marker" aria-hidden="true">
                  <span />
                  <strong>{point.marker}</strong>
                </div>
                <div className="friction-content">
                  <p>{point.title}</p>
                  <span>{point.note}</span>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section network-section" id="evidence-network">
        <div className="home-shell">
          <div className="network-panel">
            <div className="section-copy-block network-copy-block">
              <span className="section-eyebrow section-eyebrow-inverse">Evidence Network</span>
              <h2>One connected layer from question to decision.</h2>
              <p>
                EPI Engine organizes cohorts, outcomes, determinants, methods, quality, and evidence labels into a
                connected intelligence layer.
              </p>
            </div>
            <div className="network-visual" aria-hidden="true">
              <div className="network-visual-shell">
                <div className="network-status-row">
                  <span className="network-status-chip">Connected intelligence layer</span>
                  <span className="network-status-chip network-status-chip-quality">Quality attached</span>
                </div>
                <div className="network-graph-shell">
                  <div className="network-flow">
                    {networkFlowSteps.map((step, index) => (
                      <div key={step} className="network-flow-item">
                        <div className={`network-step${step === "Evidence" ? " network-step-evidence" : ""}`}>{step}</div>
                        {index < networkFlowSteps.length - 1 ? <div className="network-connector" /> : null}
                      </div>
                    ))}
                  </div>
                  <div className="network-orbit">
                    {networkSupportCards.map((card) => (
                      <div key={card} className="network-support-card">
                        <span className="network-support-dot" />
                        <strong>{card}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="network-core-panel">
                    <div className="network-core-halo" />
                    <div className="network-core-card">
                      <span>Connected evidence layer</span>
                      <strong>Evidence Graph</strong>
                      <p>Cohorts, methods, determinants, labels, and quality remain attached through the decision path.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="evidence-agent">
        <div className="home-shell">
          <div className="section-copy-block">
            <span className="section-eyebrow">Evidence Agent</span>
            <h2>A guided workflow, not a generic chatbot.</h2>
            <p>
              Each step keeps methodology guardrails, evidence labels, and quality review visible before decisions are
              exported.
            </p>
          </div>
          <div className="workflow-panel">
            <div className="workflow-rail">
              {workflowSteps.map((step, index) => (
                <article key={step.title} className="workflow-step">
                  <span className="workflow-index">{String(index + 1).padStart(2, "0")}</span>
                  <strong>{step.title}</strong>
                  <span className="status-chip">{step.status}</span>
                  {index < workflowSteps.length - 1 ? <div className="workflow-link" aria-hidden="true" /> : null}
                </article>
              ))}
            </div>
            <aside className="workflow-summary">
              <span className="workflow-summary-label">Governed workflow</span>
              <h3>Evidence moves forward only with method, label, and quality context intact.</h3>
              <div className="workflow-summary-metrics">
                <div>
                  <strong>6</strong>
                  <span>guided stages</span>
                </div>
                <div>
                  <strong>3</strong>
                  <span>visible guardrails</span>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section className="section" id="platform">
        <div className="home-shell">
          <div className="section-copy-block">
            <span className="section-eyebrow">Platform Architecture</span>
            <h2>Modern evidence architecture from data foundation to decision output.</h2>
          </div>
          <div className="architecture-diagram">
            {architectureLayers.map((layer, index) => (
              <article key={layer.title} className={`architecture-band architecture-band-${index + 1}`}>
                <div className="architecture-band-heading">
                  <span>{layer.label}</span>
                  <h3>{layer.title}</h3>
                </div>
                <div className="architecture-band-modules">
                  {layer.modules.map((module) => (
                    <span key={module} className="architecture-module-card">
                      {module}
                    </span>
                  ))}
                </div>
                {index < architectureLayers.length - 1 ? <div className="architecture-band-connector" aria-hidden="true" /> : null}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="solutions">
        <div className="home-shell">
          <div className="section-copy-block">
            <span className="section-eyebrow">Solutions</span>
            <h2>Configured for healthcare and life sciences evidence teams.</h2>
          </div>
          <div className="solutions-grid">
            {solutions.map((solution) => (
              <article key={solution.title} className="solution-card">
                <div className="solution-card-visual" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="solution-card-heading">
                  <span className="solution-card-marker">{solution.marker}</span>
                  <h3>{solution.title}</h3>
                </div>
                <div className="solution-list">
                  {solution.items.map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="home-shell">
          <div className="section-copy-block">
            <span className="section-eyebrow">Evidence Discipline</span>
            <h2>Clear evidence labels for what the output means and how far it should travel.</h2>
          </div>
          <div className="discipline-row">
            {disciplineLabels.map((label) => (
              <article key={label.title} className={`discipline-label discipline-label-${label.tone}`}>
                <span className="discipline-label-eyebrow">Evidence label</span>
                <strong>{label.title}</strong>
                <p>{label.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="home-shell">
          <div className="cta-panel">
            <div>
              <span className="section-eyebrow">Data → Evidence → Decision</span>
              <h2>Bring evidence generation closer to every healthcare decision.</h2>
            </div>
            <div className="cta-flow-markers" aria-hidden="true">
              <span>Data</span>
              <span>Evidence</span>
              <span>Decision</span>
            </div>
            <a href="#demo" className="button button-primary">
              Request a demo
            </a>
          </div>
        </div>
      </section>

      <section className="section demo-section" id="demo">
        <div className="home-shell">
          <div className="demo-panel">
            <div className="section-copy-block">
              <span className="section-eyebrow">Request Demo</span>
              <h2>See the evidence layer in action.</h2>
              <p>Share your role and use case to review how EPI Engine supports governed evidence generation.</p>
            </div>
            <form className="demo-form">
              <label className="demo-field">
                <span>Name</span>
                <input type="text" name="name" placeholder="Your name" />
              </label>
              <label className="demo-field">
                <span>Work email</span>
                <input type="email" name="email" placeholder="name@organization.com" />
              </label>
              <label className="demo-field">
                <span>Organization</span>
                <input type="text" name="organization" placeholder="Organization" />
              </label>
              <label className="demo-field">
                <span>Use case</span>
                <textarea name="use_case" rows={4} placeholder="Describe your evidence workflow" />
              </label>
              <button type="submit" className="button button-primary">
                Request demo
              </button>
            </form>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <div className="home-shell site-footer-inner">
          <span className="site-footer-brand">EPI Engine</span>
          <span className="site-footer-copy">Healthcare evidence intelligence for governed decisions.</span>
        </div>
      </footer>
    </main>
  );
}

function EvidenceIntelligenceMap() {
  const coreX = 494;
  const coreY = 286;
  const connectionLines = heroNodes.map((node) => ({
    title: node.title,
    d: `M ${coreX} ${coreY} C ${(coreX + node.x) / 2} ${coreY}, ${(coreX + node.x) / 2} ${node.y}, ${node.x} ${node.y}`,
  }));

  return (
    <div className="evidence-map-frame">
      <svg
        className="evidence-map-svg"
        viewBox="0 0 960 520"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Evidence Intelligence browser frame with a central Evidence Graph, six connected evidence nodes, metrics for cohorts, signals, and confidence, and a quality ok badge."
      >
        <defs>
          <linearGradient id="evidenceMapShell" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="100%" stopColor="#f3f7fa" />
          </linearGradient>
          <linearGradient id="evidenceMapCanvas" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fcfefd" />
            <stop offset="100%" stopColor="#eef4f8" />
          </linearGradient>
          <linearGradient id="evidenceMapSidebar" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0f2340" />
            <stop offset="100%" stopColor="#163557" />
          </linearGradient>
          <linearGradient id="evidenceMapStroke" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#9fd6d3" stopOpacity="0.28" />
            <stop offset="50%" stopColor="#4f83c2" stopOpacity="0.92" />
            <stop offset="100%" stopColor="#7ccdc6" stopOpacity="0.36" />
          </linearGradient>
          <linearGradient id="evidenceMapCore" x1="15%" y1="10%" x2="85%" y2="100%">
            <stop offset="0%" stopColor="#1b5283" />
            <stop offset="100%" stopColor="#12375d" />
          </linearGradient>
          <radialGradient id="evidenceMapHalo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8ad7ce" stopOpacity="0.32" />
            <stop offset="60%" stopColor="#5f8fc8" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#5f8fc8" stopOpacity="0" />
          </radialGradient>
          <filter id="evidenceMapShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="20" stdDeviation="22" floodColor="#112641" floodOpacity="0.12" />
          </filter>
          <filter id="evidenceNodeShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="11" floodColor="#18324f" floodOpacity="0.08" />
          </filter>
        </defs>

        <rect x="16" y="14" width="928" height="492" rx="30" fill="#dbe7f0" opacity="0.45" />
        <rect x="24" y="22" width="912" height="476" rx="28" fill="url(#evidenceMapShell)" stroke="#d7e2ea" filter="url(#evidenceMapShadow)" />

        <rect x="24" y="22" width="912" height="50" rx="28" fill="#f8fbfd" />
        <circle cx="54" cy="47" r="5" fill="#c5d1db" />
        <circle cx="72" cy="47" r="5" fill="#c5d1db" />
        <circle cx="90" cy="47" r="5" fill="#c5d1db" />
        <text x="122" y="52" className="evidence-map-svg-title">
          Evidence Intelligence OS
        </text>
        <g transform="translate(784 32)">
          <rect width="116" height="30" rx="15" fill="#ecf7f0" stroke="#badfc7" />
          <circle cx="20" cy="15" r="5" fill="#4f9a68" />
          <text x="36" y="20" className="evidence-map-svg-badge">
            Quality OK
          </text>
        </g>

        <rect x="42" y="88" width="92" height="392" rx="22" fill="url(#evidenceMapSidebar)" />
        <rect x="60" y="112" width="56" height="10" rx="5" fill="#edf4f8" opacity="0.9" />
        <rect x="60" y="138" width="40" height="8" rx="4" fill="#84afc7" opacity="0.8" />
        <rect x="60" y="194" width="56" height="40" rx="14" fill="#173451" stroke="#2a5578" />
        <rect x="60" y="258" width="56" height="8" rx="4" fill="#d8e5ef" opacity="0.24" />
        <rect x="60" y="282" width="56" height="8" rx="4" fill="#d8e5ef" opacity="0.2" />
        <rect x="60" y="306" width="56" height="8" rx="4" fill="#d8e5ef" opacity="0.16" />
        <rect x="60" y="432" width="56" height="28" rx="14" fill="#173451" stroke="#2a5578" />

        <rect x="148" y="88" width="764" height="392" rx="24" fill="url(#evidenceMapCanvas)" />
        <circle cx="286" cy="156" r="126" fill="#7fd0c6" opacity="0.12" />
        <circle cx="742" cy="396" r="118" fill="#6d98ca" opacity="0.08" />
        <circle cx="492" cy="284" r="174" fill="url(#evidenceMapHalo)" />
        <circle cx="492" cy="284" r="144" fill="none" stroke="#e7eef4" strokeWidth="2" />
        <circle cx="492" cy="284" r="108" fill="none" stroke="#dbe6ee" strokeWidth="2" />

        {connectionLines.map((line) => (
          <path key={line.title} d={line.d} stroke="url(#evidenceMapStroke)" strokeWidth="5" strokeLinecap="round" fill="none" />
        ))}

        {heroNodes.map((node) => (
          <g key={node.title} transform={`translate(${node.x - 72} ${node.y - 26})`} filter="url(#evidenceNodeShadow)">
            <rect
              width="144"
              height="52"
              rx="26"
              fill={node.title === "Quality" ? "#edf8f1" : "#ffffff"}
              stroke={node.title === "Quality" ? "#b9dec5" : "#d7e2ea"}
            />
            <text
              x="72"
              y="32"
              textAnchor="middle"
              className={node.title === "Quality" ? "evidence-map-svg-node evidence-map-svg-node-quality" : "evidence-map-svg-node"}
            >
              {node.title}
            </text>
          </g>
        ))}

        <g transform="translate(378 170)">
          <circle cx="114" cy="114" r="128" fill="#7fd0c6" opacity="0.16" />
          <circle cx="114" cy="114" r="104" fill="url(#evidenceMapCore)" />
          <circle cx="114" cy="114" r="104" fill="none" stroke="#7bcfca" strokeOpacity="0.34" />
          <text x="114" y="104" textAnchor="middle" className="evidence-map-svg-core-label">
            Evidence
          </text>
          <text x="114" y="144" textAnchor="middle" className="evidence-map-svg-core-value">
            Graph
          </text>
        </g>

        {heroMetrics.map((metric, index) => (
          <g key={metric.title} transform={`translate(${196 + index * 188} 402)`} filter="url(#evidenceNodeShadow)">
            <rect
              width="174"
              height="60"
              rx="18"
              fill={metric.title === "Confidence" ? "#eef7f2" : "#ffffff"}
              stroke={metric.title === "Confidence" ? "#c5e2ce" : "#d7e2ea"}
            />
            <text x="18" y="24" className="evidence-map-svg-metric-label">
              {metric.title}
            </text>
            <text x="18" y="47" className="evidence-map-svg-metric-value">
              {metric.value}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
