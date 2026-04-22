import type { MedicationRoute, MedicationStatus } from "./common";

export type Medication = {
  name: string;
  route: MedicationRoute;
  status: MedicationStatus;
  competitionClass: string;
};
