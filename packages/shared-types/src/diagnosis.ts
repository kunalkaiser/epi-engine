import type { DiagnosisSystem } from "./common";

export type Diagnosis = {
  code: string;
  system: DiagnosisSystem;
  label: string;
  prevalencePer100k: number | null;
};
