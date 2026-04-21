export const demographicKeys = [
    "pct_american_indian_alaska_native",
    "pct_asian",
    "pct_black_or_african_american",
    "pct_native_hawaiian_pacific_islander",
    "pct_two_or_more_races",
    "pct_white",
] as const;

export type AdjustableField =
    | "per_pupil_total_raw"
    | "nces_poverty"
    | "nces_freelunch"
    | "exp_rate"
    | "inexp_rate"
    | (typeof demographicKeys)[number];

const TEACHER_EXPERIENCE_GROUP = "teacher_experience";

export function toGroupKey(field: AdjustableField) {
    if (field === "exp_rate" || field === "inexp_rate") {
        return TEACHER_EXPERIENCE_GROUP;
    }
    return field;
}

export function formatDemographicLabel(key: (typeof demographicKeys)[number]) {
    return key
        .replace("pct_", "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (match) => match.toUpperCase());
}
