from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class DatasetInfo(BaseModel):
    key: str
    description: str
    filters: list[str]
    requires_filter_for_download: bool


class SchoolItem(BaseModel):
    school_key: int
    school_year_start: int
    school_year_label: str
    dist_name: str
    school_name: str


class FiltersResponse(BaseModel):
    years: list[int]
    districts: list[str]
    genders: list[str]
    races: list[str]
    ethnicities: list[str]


class DataPreviewResponse(BaseModel):
    dataset: str
    limit: int
    offset: int
    row_count: int
    rows: list[dict[str, object]]


class DistrictRankingItem(BaseModel):
    district_key: int
    district_name: str
    year: int
    school_count: int
    avg_per_pupil_funding: float | None
    avg_achievement: float | None
    funding_rank: int


class DistrictRankingsResponse(BaseModel):
    year: int
    limit: int
    next_cursor: str | None
    items: list[DistrictRankingItem]


class DistrictSchoolItem(BaseModel):
    district_key: int
    district_name: str
    school_key: int
    school_name: str
    year: int
    per_pupil_total_raw: float | None
    ach_all: float | None


class DistrictSchoolsResponse(BaseModel):
    district_key: int
    year: int
    limit: int
    next_cursor: str | None
    items: list[DistrictSchoolItem]


class SchoolPerformancePoint(BaseModel):
    year: int
    per_pupil_total_raw: float | None
    ach_all: float | None
    grw_all: float | None
    abs_all: float | None


class SchoolPerformanceResponse(BaseModel):
    school_key: int
    school_name: str | None
    district_name: str | None
    from_year: int | None
    to_year: int | None
    points: list[SchoolPerformancePoint]


class SchoolSimulationYearStatus(BaseModel):
    year: int
    is_simulatable: bool
    missing_features: list[str]


class SchoolSimulationMetadataResponse(BaseModel):
    school_key: int
    available_years: list[int]
    required_features: list[str]
    latest_year: int | None
    latest_simulatable_year: int | None
    selected_year: int | None
    is_simulatable: bool
    missing_features: list[str]
    year_status: list[SchoolSimulationYearStatus]
