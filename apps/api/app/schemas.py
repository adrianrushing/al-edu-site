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
