from pydantic import BaseModel, ConfigDict, Field

from apps.api.contracts import IncidenceAggregate, IndicationScore, PrevalenceAggregate, RankedIndication


class RepurposingOpportunity(BaseModel):
    rank: int = Field(ge=1)
    indication_name: str
    epi_scores: dict
    best_compound: str | None = None
    best_compound_chembl_id: str | None = None
    mechanistic_confidence: int = Field(ge=0, le=100)
    evidence_label: str
    regulatory_pathway: str
    opportunity_score: float


class RepurposingOpportunitiesResponse(BaseModel):
    opportunities: list[RepurposingOpportunity]
    total: int
    methodology: str
    generated_at: str


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class DiseaseListItem(BaseModel):
    disease_id: str
    disease_name: str
    regions: list[str]
    year_min: int
    year_max: int

    model_config = ConfigDict(str_strip_whitespace=True)


class DiseasesResponse(BaseModel):
    items: list[DiseaseListItem]
    pagination: PaginationMeta


class IncidenceResponse(BaseModel):
    items: list[IncidenceAggregate]
    pagination: PaginationMeta


class PrevalenceResponse(BaseModel):
    items: list[PrevalenceAggregate]
    pagination: PaginationMeta


class TopIndicationsResponse(BaseModel):
    items: list[IndicationScore]
    pagination: PaginationMeta
    scoring_profile: dict | None = None
    methodology: dict | None = None


class RankedIndicationsResponse(BaseModel):
    items: list[RankedIndication]
    pagination: PaginationMeta
    scoring_profile: dict | None = None
    methodology: dict | None = None
    caveats: list[str] = Field(default_factory=list)
