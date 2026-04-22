import type { Sex } from "./common";

export type PatientSummary = {
  populationLabel: string;
  ageBand: string;
  sex: Sex;
  count: number;
};
