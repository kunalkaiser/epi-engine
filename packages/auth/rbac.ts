export const EPIOS_ROLES = [
  "admin",
  "analyst",
  "payer_aggregate_only",
  "trial_coordinator",
  "read_only_gov",
] as const;

export type EpiOSRole = (typeof EPIOS_ROLES)[number];

export function canAccessPrioritization(role: EpiOSRole): boolean {
  return role === "admin" || role === "analyst" || role === "trial_coordinator";
}
