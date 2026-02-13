import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi, formatDistrictName } from './client'
import type {
    DistrictNamesResponse,
    ImportantFeaturesResponse,
    SelectDistrictResponse,
    AdjustFeaturesResponse,
    AdjustmentsPayload,
    PredictionResponse,
} from './types'

// Query keys
export const queryKeys = {
    districtNames: ['districtNames'] as const,
    importantFeatures: ['importantFeatures'] as const,
    prediction: ['prediction'] as const,
}

/**
 * Hook to fetch district names
 */
export function useDistrictNames() {
    return useQuery({
        queryKey: queryKeys.districtNames,
        queryFn: () => fetchApi<DistrictNamesResponse>('/api/get-district-names'),
    })
}

/**
 * Hook to select a district (mutation)
 */
export function useSelectDistrict() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (districtName: string) => {
            const safeName = formatDistrictName(districtName)
            return fetchApi<SelectDistrictResponse>(`/api/select-district/${safeName}`, {
                method: 'POST',
            })
        },
        onSuccess: () => {
            // Invalidate related queries after successful selection
            queryClient.invalidateQueries({ queryKey: queryKeys.importantFeatures })
        },
    })
}

/**
 * Hook to fetch important features
 */
export function useImportantFeatures() {
    return useQuery({
        queryKey: queryKeys.importantFeatures,
        queryFn: () => fetchApi<ImportantFeaturesResponse>('/api/get-important-features'),
        enabled: false, // Only fetch when explicitly called
    })
}

/**
 * Hook to submit feature adjustments (mutation)
 */
export function useAdjustFeatures() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (adjustments: AdjustmentsPayload) =>
            fetchApi<AdjustFeaturesResponse>('/api/adjust-data', {
                method: 'POST',
                body: JSON.stringify(adjustments),
            }),
        onSuccess: () => {
            // Invalidate prediction query after adjustments
            queryClient.invalidateQueries({ queryKey: queryKeys.prediction })
        },
    })
}

/**
 * Hook to fetch prediction results
 */
export function usePredictAdjustedData() {
    return useQuery({
        queryKey: queryKeys.prediction,
        queryFn: () => fetchApi<PredictionResponse>('/api/predict-adjusted-data'),
        enabled: false, // Only fetch when explicitly called
    })
}
