# API Endpoints Reference

This document provides a reference for all API endpoints in the application. When adding new endpoints, please add them to this table to keep the documentation up to date.

| Endpoint | Table(s) Queried | What it Returns | Where it is Used |
|----------|------------------|-----------------|------------------|
| `GET /health` | None (executes `SELECT 1`) | `HealthResponse` (status: "ok", database: "ok") | Health checking endpoint to verify API and database connectivity |
| `GET /datasets` | None (uses `DATASETS` from `app.datasets`) | `list[DatasetInfo]` | Lists all available datasets with their metadata |
| `GET /schools` | `core.dim_school_info` | `list[SchoolItem]` | Lists schools with optional filtering by name, year, and pagination |
| `GET /filters` | `core.dim_school_info`, `ref.gender_canonical`, `ref.race_canonical`, `ref.ethnicity_canonical` | `FiltersResponse` | Provides available filter values for years, districts, genders, races, and ethnicities |
| `GET /data/{dataset}` | Dataset-specific tables (determined by dataset config) | `DataPreviewResponse` | Returns a preview of dataset data with applied filters and pagination |
| `GET /download/{dataset}.csv` | Dataset-specific tables (determined by dataset config) | CSV file stream (`StreamingResponse`) | Allows downloading full dataset as CSV with applied filters |
| `GET /schools/{school_key}/metadata` | `core.dim_school_info` | `SchoolMetadataResponse` (available years + latest year) | Powers simulator school metadata popup and latest-year selection |
| `GET /predict/baseline/{school_key}/{year}` | `core.dim_school_info`, `core.fact_school_outcomes_wide`, `core.fact_edunomics`, `core.fact_teacher_experience`, `core.fact_student_demographics` | Dictionary of baseline features | Fetches exact baseline features for a given school and year, formatted for model prediction |
| `POST /predict/{target_variable}` | None (uses cached model files) | Prediction result dictionary | Makes predictions for a target variable using pre-trained machine learning models |
| `GET /rankings/districts` | `core.mv_district_year_funding_performance` (or computed live from core tables) | `DistrictRankingsResponse` | Returns district rankings based on funding and performance metrics |
| `GET /rankings/districts/{district_key}/schools` | `core.dim_district`, `core.dim_school`, `core.dim_school_info`, `core.fact_edunomics`, `core.fact_school_outcomes_wide` | `DistrictSchoolsResponse` | Returns schools within a specific district with funding and achievement data |
| `GET /rankings/schools/{school_key}/performance` | `core.fact_edunomics`, `core.fact_school_outcomes_wide`, `core.dim_school_info` | `SchoolPerformanceResponse` | Returns historical performance data for a specific school over time |

## Maintenance Rule

When adding new API endpoints to the application, you must also add an entry for that endpoint in this markdown file (`API_ENDPOINTS.md`) following the same format as the existing entries. This ensures the documentation remains accurate and useful for developers and integrators.

**To add a new endpoint:**
1. Determine the endpoint path and HTTP method
2. Identify which database tables are queried (if any)
3. Describe what the endpoint returns (response model or data type)
4. Provide a brief description of where/how it is used
5. Add a new row to the table above with this information
