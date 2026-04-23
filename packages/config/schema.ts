export type RuntimeEnvironment = "development" | "staging" | "production";

export type EpiOSRuntimeConfig = {
  environment: RuntimeEnvironment;
  apiBaseUrl: string;
  telemetryEnabled: boolean;
  aggregateOnlyMode: boolean;
};
