from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetConfig:
    key: str
    table_name: str
    columns: tuple[str, ...]
    description: str
    requires_filter_for_download: bool = False


DATASETS: dict[str, DatasetConfig] = {
    "student_demographics": DatasetConfig(
        key="student_demographics",
        table_name="fact_student_demographics",
        columns=(
            "year",
            "grade",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
            "demographic_count",
        ),
        description="Student demographic counts by school, subgroup, and year.",
        requires_filter_for_download=True,
    ),
    "teacher_demographics": DatasetConfig(
        key="teacher_demographics",
        table_name="fact_teacher_demographics",
        columns=(
            "year",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
            "demographic_count",
            "demographic_rate",
            "imputed_flag",
            "imputation_method",
        ),
        description="Teacher demographics with optional imputation indicators.",
    ),
    "accountability": DatasetConfig(
        key="accountability",
        table_name="fact_accountability",
        columns=(
            "year",
            "indicator",
            "grade",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
            "score",
        ),
        description="School accountability indicators and scores.",
    ),
    "edunomics": DatasetConfig(
        key="edunomics",
        table_name="fact_edunomics",
        columns=(
            "year",
            "ncesenroll",
            "gradespan",
            "level",
            "state_local_per_pupil",
            "state_local_fund",
            "nces_fund",
            "nces_poverty",
            "title_i_status",
            "nces_charter",
            "nces_magnet",
            "nces_freelunch",
            "nces_reducedlunch",
        ),
        description="Per-pupil funding and school finance fields.",
    ),
    "teacher_effectiveness": DatasetConfig(
        key="teacher_effectiveness",
        table_name="fact_teacher_effectiveness",
        columns=(
            "year",
            "score",
            "atot_completion_rate_designation",
            "title_i_status",
        ),
        description="Teacher effectiveness summary metrics.",
    ),
    "teacher_experience": DatasetConfig(
        key="teacher_experience",
        table_name="fact_teacher_experience",
        columns=(
            "year",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
            "total_count",
            "exp_count",
            "exp_rate",
            "inexp_count",
            "inexp_rate",
        ),
        description="Teacher experience distribution by subgroup.",
    ),
}


DIM_COLUMNS: tuple[str, ...] = (
    "school_key",
    "school_year_label",
    "school_year_start",
    "dist_name",
    "school_name",
)


COMMON_FILTERS: tuple[str, ...] = (
    "year",
    "school_key",
    "district",
    "school",
    "gender",
    "race",
    "ethnicity",
    "sub_population",
    "grade",
)
