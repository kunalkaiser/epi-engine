import type { LabInterpretation } from "./common";

export type LabResult = {
  testCode: string;
  testName: string;
  value: number;
  unit: string;
  referenceLow: number | null;
  referenceHigh: number | null;
  interpretation: LabInterpretation;
  collectedOn: string;
};
