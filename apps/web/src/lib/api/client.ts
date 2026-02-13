/**
 * Type-safe wrapper around fetch for API calls
 */
export async function fetchApi<T>(
    url: string,
    options?: RequestInit
): Promise<T> {
    const response = await fetch(url, {
        credentials: 'include', // Include credentials for session handling
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    })

    if (!response.ok) {
        throw new Error(`API call failed: ${response.statusText}`)
    }

    return response.json()
}

/**
 * Format district name for URL (replace spaces with hyphens)
 */
export function formatDistrictName(districtName: string): string {
    return districtName.replace(/\s+/g, '-')
}
