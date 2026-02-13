import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import { Slash } from 'lucide-react'
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { usePredictAdjustedData } from '@/lib/api/queries'

export const Route = createFileRoute('/adjusted-features')({
    component: AdjustedFeaturesComponent,
})

function AdjustedFeaturesComponent() {
    const { data: prediction, refetch } = usePredictAdjustedData()

    useEffect(() => {
        // Fetch prediction when component mounts
        refetch()
    }, [refetch])

    return (
        <div className="flex flex-col items-center pt-[20vh] gap-6">
            <div className="absolute top-4 left-4">
                <Breadcrumb>
                    <BreadcrumbList>
                        <BreadcrumbItem>
                            <BreadcrumbLink href="/">Home</BreadcrumbLink>
                        </BreadcrumbItem>
                        <BreadcrumbSeparator>
                            <Slash className="w-4 h-4" />
                        </BreadcrumbSeparator>
                        <BreadcrumbItem>
                            <BreadcrumbLink href="/select-district">Select District</BreadcrumbLink>
                        </BreadcrumbItem>
                        <BreadcrumbSeparator>
                            <Slash className="w-4 h-4" />
                        </BreadcrumbSeparator>
                        <BreadcrumbItem>
                            <BreadcrumbLink href="/adjusted-features">Adjust Features</BreadcrumbLink>
                        </BreadcrumbItem>
                    </BreadcrumbList>
                </Breadcrumb>
            </div>

            {/* Display adjusted features */}
            <h1 className="text-4xl font-bold mb-8">Adjusted Performance Metrics</h1>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
                {/* District % Increase */}
                <div className="text-center border p-6 rounded-lg shadow-md bg-card text-card-foreground">
                    <h2 className="text-xl font-semibold">District % Increase</h2>
                    <div>{prediction?.districtPercentIncrease || 'N/A'}</div>
                </div>

                {/* Similar Districts % Increase */}
                <div className="text-center border p-6 rounded-lg shadow-md bg-card text-card-foreground">
                    <h2 className="text-xl font-semibold">Similar Districts % Increase</h2>
                    <div>{prediction?.similarDistrictsPercentIncrease || 'N/A'}</div>
                </div>

                {/* State % Increase */}
                <div className="text-center border p-6 rounded-lg shadow-md bg-card text-card-foreground">
                    <h2 className="text-xl font-semibold">State % Increase</h2>
                    <div>{prediction?.statePercentIncrease || 'N/A'}</div>
                </div>
            </div>
        </div>
    )
}
