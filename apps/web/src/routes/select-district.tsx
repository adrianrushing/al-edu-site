import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Slash } from 'lucide-react'

// API hooks
import {
    useDistrictNames,
    useSelectDistrict,
    useImportantFeatures,
    useAdjustFeatures,
} from '@/lib/api/queries'

// UI components
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import DistrictDataTable from '@/components/ui/DistrictDataTable'
import { DistrictFeatureForm } from '@/components/ui/forms/DistrictFeatureForm'
import { GradeFeatureForm } from '@/components/ui/forms/GradeFeatureForm'

// Types
import type { DistrictFeatureFormValues } from '@/lib/validation/districtFeatureSchema'
import type { GradeFeatureFormValues } from '@/lib/validation/gradeFeatureSchema'

export const Route = createFileRoute('/select-district')({
    component: SelectDistrictComponent,
})

function SelectDistrictComponent() {
    const navigate = useNavigate()

    // State
    const [selectedDistrict, setSelectedDistrict] = useState('')
    const [showData, setShowData] = useState(false)
    const [topLevelFeatures, setTopLevelFeatures] = useState<string[]>([])
    const [bottomLevelFeatures, setBottomLevelFeatures] = useState<string[]>([])

    // Refs for form submission handlers
    const districtFormRef = useRef<((values?: DistrictFeatureFormValues) => Promise<DistrictFeatureFormValues | null>) | null>(null)
    const gradeFormRef = useRef<((values?: GradeFeatureFormValues) => Promise<GradeFeatureFormValues | null>) | null>(null)
    const tableRef = useRef<HTMLDivElement>(null)

    // API hooks
    const { data: districtNamesData, isLoading: isLoadingDistricts } = useDistrictNames()
    const selectDistrictMutation = useSelectDistrict()
    const { refetch: fetchImportantFeatures } = useImportantFeatures()
    const adjustFeaturesMutation = useAdjustFeatures()

    // Handle "Go" button click
    const handleGoClick = async () => {
        if (!selectedDistrict) {
            console.log("User hasn't selected a district.")
            return
        }

        try {
            // Select district
            await selectDistrictMutation.mutateAsync(selectedDistrict)
            console.log(`Successfully selected district: ${selectedDistrict}`)

            // Fetch important features
            const { data: features } = await fetchImportantFeatures()
            console.log('Successfully fetched important features:', features)

            setTopLevelFeatures(features?.topLevelFeatures || [])
            setBottomLevelFeatures(features?.bottomLevelFeatures || [])
        } catch (err) {
            console.error('Error selecting district or fetching features:', err)
            return
        }

        setShowData(true)
    }

    // Handle district form submission (optional callback)
    const handleDistrictSubmit = (values: DistrictFeatureFormValues) => {
        console.log('District form submitted:', values)
    }

    // Handle grade form submission (optional callback)
    const handleGradeSubmit = (values: GradeFeatureFormValues) => {
        console.log('Grade form submitted:', values)
    }

    // Handle adjustment submission
    const handleAdjustmentSubmit = async () => {
        if (districtFormRef.current && gradeFormRef.current) {
            const districtValues = await districtFormRef.current()
            const gradeValues = await gradeFormRef.current()

            if (!districtValues || !gradeValues) {
                console.warn('Form validation failed.')
                return
            }

            console.log('✅ Validation passed. Navigating...')
            console.log('District Adjustments:', districtValues)
            console.log('Grade Adjustments:', gradeValues)

            // Rename grade level adjustments
            const renamedGradeValues: Record<string, string> = {}
            Object.keys(gradeValues).forEach((key) => {
                renamedGradeValues[`grade_${key}`] = gradeValues[key as keyof GradeFeatureFormValues]
            })

            // Rename district level adjustments
            const renamedDistrictValues: Record<string, string> = {}
            Object.keys(districtValues).forEach((key) => {
                renamedDistrictValues[`district_${key}`] = districtValues[key as keyof DistrictFeatureFormValues]
            })

            const combinedAdjustments = {
                ...renamedDistrictValues,
                ...renamedGradeValues,
            }

            // Map to feature names
            const allFeatures = [...topLevelFeatures, ...bottomLevelFeatures].map((feature) =>
                feature.replace(/ /g, '_')
            )

            const renamedAdjustments: Record<string, string | number> = {}
            Object.keys(combinedAdjustments).forEach((key, index) => {
                if (index < allFeatures.length) {
                    renamedAdjustments[allFeatures[index]] = combinedAdjustments[key]
                }
            })

            console.log('Renamed Adjustments Object: ', renamedAdjustments)

            // Send adjustments to backend
            try {
                const result = await adjustFeaturesMutation.mutateAsync(renamedAdjustments)
                console.log('✅ Adjustments sent:', result)
            } catch (err) {
                console.error('❌ Failed to send adjustments:', err)
            }

            // Navigate to adjusted features page
            navigate({ to: '/adjusted-features' })
        }
    }

    // Auto-fill with random values (for testing)
    const fillRandomAdjustments = () => {
        const getRandom = () => (Math.random() * 200 - 100).toFixed(2)

        const randomDistrictData: Partial<DistrictFeatureFormValues> = {}
        const randomGradeData: Partial<GradeFeatureFormValues> = {}

        for (let i = 1; i <= 10; i++) {
            randomDistrictData[`feature${i}` as keyof DistrictFeatureFormValues] = getRandom()
        }

        for (let i = 1; i <= 2; i++) {
            randomGradeData[`feature${i}` as keyof GradeFeatureFormValues] = getRandom()
        }


        // Fill the forms directly via refs
        if (districtFormRef.current) districtFormRef.current(randomDistrictData as DistrictFeatureFormValues)
        if (gradeFormRef.current) gradeFormRef.current(randomGradeData as GradeFeatureFormValues)
    }

    return (
        <div className="min-h-screen relative pb-24">
            {/* Breadcrumb */}
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
                    </BreadcrumbList>
                </Breadcrumb>
            </div>

            {/* District Selection */}
            <div className="flex flex-col items-center pt-[20vh] gap-6">
                <h1 className="text-4xl font-bold">Select a School District</h1>
                <div className="w-72 border-t border-gray-500" />

                <div className="flex items-center gap-4">
                    <Select onValueChange={setSelectedDistrict}>
                        <SelectTrigger className="w-60">
                            <SelectValue placeholder="Choose a district" />
                        </SelectTrigger>
                        <SelectContent>
                            {isLoadingDistricts && <SelectItem value="loading" disabled>Loading...</SelectItem>}
                            {districtNamesData?.districtNames.map((district) => (
                                <SelectItem key={district} value={district}>
                                    {district}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {selectedDistrict && (
                        <Button className="shrink-0" onClick={handleGoClick}>
                            Go
                        </Button>
                    )}
                </div>
            </div>

            {/* Data Display Section */}
            {showData && (
                <motion.div
                    ref={tableRef}
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="mt-12 mx-auto w-2/3"
                >
                    {/* Performance Metrics */}
                    <div className="flex flex-col items-center pt-[1vh] gap-6 mb-8">
                        <div className="flex flex-col text-center pt-[1vh] gap-4">
                            <h1 className="text-3xl font-bold">
                                Performance Metrics for <span className="text-blue-400">{selectedDistrict}</span>
                            </h1>
                            <div className="mx-auto w-full h-px bg-gray-500" />
                        </div>
                        <p className="list-inside list-decimal text-sm text-center sm:text-center font-[family-name:var(--font-geist-mono)]">
                            [display performance metrics here.]
                        </p>
                    </div>

                    {/* Adjustment Forms */}
                    <div className="mt-12 space-y-6 mb-20">
                        <div className="text-center gap-10">
                            <h2 className="text-3xl font-bold">Make adjustments</h2>
                            <div className="w-72 mx-auto border-t border-gray-500 mt-4" />
                        </div>

                        <div className="flex justify-center">
                            <p className="max-w-3xl px-4 list-inside list-decimal text-sm text-center sm:text-center font-[family-name:var(--font-geist-mono)]">
                                Please enter real-number values that represent (%) adjustments for each feature to see
                                how this school district would perform differently given some changes.
                            </p>
                        </div>

                        <div className="flex justify-center mt-2">
                            <Button variant="outline" onClick={fillRandomAdjustments}>
                                Auto-fill with Random Adjustments
                            </Button>
                        </div>

                        <div>
                            <DistrictFeatureForm
                                setSubmitHandler={(fn) => (districtFormRef.current = fn)}
                                onSubmit={handleDistrictSubmit}
                                featureNames={topLevelFeatures}
                            />
                        </div>

                        <div>
                            <GradeFeatureForm
                                setSubmitHandler={(fn) => (gradeFormRef.current = fn)}
                                onSubmit={handleGradeSubmit}
                                featureNames={bottomLevelFeatures}
                            />
                        </div>

                        <div className="flex justify-center mt-8">
                            <Button onClick={handleAdjustmentSubmit}>Apply Adjustments</Button>
                        </div>
                    </div>

                    {/* Data Table */}
                    <div className="flex flex-col text-center pt-[1vh] gap-4">
                        <h1 className="text-3xl font-bold">Raw Data</h1>
                        <div className="mx-auto h-px bg-gray-500 mb-8 inline-block w-[50%]" />
                    </div>

                    <DistrictDataTable selectedDistrict={selectedDistrict} />
                </motion.div>
            )}
        </div>
    )
}
