import type { Diagnosis } from "./diagnosis";
import type { Encounter } from "./encounter";
import type { IncidenceAggregate } from "./incidence-aggregate";
import type { IndicationScore } from "./indication-score";
import type { LabResult } from "./lab-result";
import type { Medication } from "./medication";
import type { PatientSummary } from "./patient-summary";
import type { PrevalenceAggregate } from "./prevalence-aggregate";

export const patientSummaryExample: PatientSummary = {
  populationLabel: "Adults with type 2 diabetes",
  ageBand: "45-64",
  sex: "female",
  count: 18240,
};

export const diagnosisExample: Diagnosis = {
  code: "E11.9",
  system: "ICD10",
  label: "Type 2 diabetes mellitus without complications",
  prevalencePer100k: 9630.5,
};

export const medicationExample: Medication = {
  name: "Metformin",
  route: "oral",
  status: "generic",
  competitionClass: "biguanide",
};

export const labResultExample: LabResult = {
  testCode: "A1C",
  testName: "Hemoglobin A1c",
  value: 7.2,
  unit: "%",
  referenceLow: 4.0,
  referenceHigh: 5.6,
  interpretation: "high",
  collectedOn: "2026-03-01",
};

export const encounterExample: Encounter = {
  encounterType: "outpatient",
  regionCode: "US-CA",
  periodStart: "2025-01-01",
  periodEnd: "2025-12-31",
  aggregateCount: 248900,
};

export const incidenceAggregateExample: IncidenceAggregate = {
  diseaseId: "t2d",
  diseaseName: "Type 2 diabetes",
  regionCode: "US",
  year: 2025,
  incidentCases: 1540000,
  population: 334900000,
  incidencePer100k: 459.8,
};

export const prevalenceAggregateExample: PrevalenceAggregate = {
  diseaseId: "t2d",
  diseaseName: "Type 2 diabetes",
  regionCode: "US",
  year: 2025,
  prevalentCases: 32200000,
  population: 334900000,
  prevalencePer100k: 9614.8,
};

export const indicationScoreExample: IndicationScore = {
  indicationId: "t2d-us",
  indicationName: "Type 2 diabetes",
  incidenceScore: 84.0,
  unmetNeedScore: 61.0,
  marketSizeScore: 88.0,
  competitionScore: 42.0,
  totalScore: 68.8,
};
