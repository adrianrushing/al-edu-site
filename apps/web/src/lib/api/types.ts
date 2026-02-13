// API Response Types
export interface DistrictNamesResponse {
    districtNames: string[]
}

export interface ImportantFeaturesResponse {
    topLevelFeatures: string[]
    bottomLevelFeatures: string[]
}

export interface SelectDistrictResponse {
    message: string
}

export interface AdjustFeaturesResponse {
    message: string
}

export interface PredictionResponse {
    districtPercentIncrease: string
    similarDistrictsPercentIncrease: string
    statePercentIncrease: string
}

// Request Payload Types
export interface AdjustmentsPayload {
    [key: string]: number | string
}

// Data types for forms
export interface DistrictFormValues {
    feature1: string
    feature2: string
    feature3: string
    feature4: string
    feature5: string
    feature6: string
    feature7: string
    feature8: string
    feature9: string
    feature10: string
}

export interface GradeFormValues {
    feature1: string
    feature2: string
}
