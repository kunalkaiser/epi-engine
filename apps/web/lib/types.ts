export type PaginationMeta = {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
};

export type DiseaseListItem = {
  diseaseId: string;
  diseaseName: string;
  regions: string[];
  yearMin: number;
  yearMax: number;
};

export type DiseasesResponse = {
  items: DiseaseListItem[];
  pagination: PaginationMeta;
};

export type IncidenceAggregate = {
  diseaseId: string;
  diseaseName: string;
  regionCode: string;
  year: number;
  incidentCases: number;
  population: number;
  incidencePer100k: number;
};

export type PrevalenceAggregate = {
  diseaseId: string;
  diseaseName: string;
  regionCode: string;
  year: number;
  prevalentCases: number;
  population: number;
  prevalencePer100k: number;
};

export type IndicationScore = {
  indicationId: string;
  indicationName: string;
  incidenceScore: number;
  unmetNeedScore: number;
  marketSizeScore: number;
  competitionScore: number;
  totalScore: number;
};

export type IncidenceResponse = {
  items: IncidenceAggregate[];
  pagination: PaginationMeta;
};

export type PrevalenceResponse = {
  items: PrevalenceAggregate[];
  pagination: PaginationMeta;
};

export type TopIndicationsResponse = {
  items: IndicationScore[];
  pagination: PaginationMeta;
};

export type HealthResponse = {
  status: string;
  environment: string;
};
