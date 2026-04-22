# EPI Engine - Product Wiki

## 1. What We Are Building

EPI Engine is a healthcare decision-support platform that helps:
- pharma companies prioritize indications
- researchers understand disease landscapes
- healthcare systems analyze population health

We are NOT building:
- a generic analytics dashboard
- a patient-level clinical decision tool
- a regulated medical device (initially)

---

## 2. Core Value Proposition

We answer:

"What disease indications should we invest in, and why?"

We do this using:
- epidemiological data (incidence, prevalence)
- risk factors and determinants
- simple, transparent scoring models

---

## 3. V1 Product Scope (STRICT)

We are building ONLY:

1. Disease Explorer
   - incidence and prevalence trends
   - filters by region, time, population

2. Indication Prioritizer
   - ranked list of indications
   - scoring based on:
     - incidence
     - unmet need
     - market size proxy
     - competition

3. Cohort Summary (NOT patient-level export)
   - aggregate counts
   - demographic breakdowns

---

## 4. What We Are NOT Building (Yet)

- patient-level risk prediction
- real-time surveillance system
- full ML simulation engine
- clinical decision support (regulated)

---

## 5. Architecture Principles

- Backend: FastAPI
- Frontend: Next.js + TypeScript
- Analytics DB: ClickHouse
- No premature microservices

---

## 6. Data Principles

- Prefer aggregate data over patient-level
- Use synthetic or de-identified data in dev
- Never expose PHI
- Data quality matters more than model complexity

---

## 7. ML Philosophy

We use simple, interpretable models first:
- clustering (for subgroups)
- scoring (for prioritization)

We avoid black-box models in V1.

---

## 8. UX Philosophy

- Fast insights > beautiful dashboards
- 5-10 minute workflows
- exportable outputs (PowerPoint, CSV)

---

## 9. Success Criteria (V1)

A pharma user should be able to:
- identify a top indication in < 15 minutes
- understand WHY it ranks high
- export results for internal discussion

---

## 10. Long-Term Vision (DO NOT BUILD YET)

- simulation engine
- causal inference engine
- real-time epidemiology tracking
- regulatory-grade decision tools
