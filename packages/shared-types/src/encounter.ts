import type { EncounterType } from "./common";

export type Encounter = {
  encounterType: EncounterType;
  regionCode: string;
  periodStart: string;
  periodEnd: string;
  aggregateCount: number;
};
