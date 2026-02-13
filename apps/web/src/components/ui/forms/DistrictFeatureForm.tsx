import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DistrictFeatureSchema, type DistrictFeatureFormValues } from '@/lib/validation/districtFeatureSchema'
import { useEffect } from 'react'

interface DistrictFeatureFormProps {
    setSubmitHandler?: (handler: (values?: DistrictFeatureFormValues) => Promise<DistrictFeatureFormValues | null>) => void
    onSubmit?: (values: DistrictFeatureFormValues) => void
    featureNames?: string[]
}

export function DistrictFeatureForm({ setSubmitHandler, onSubmit, featureNames = [] }: DistrictFeatureFormProps) {
    const form = useForm<DistrictFeatureFormValues>({
        resolver: zodResolver(DistrictFeatureSchema),
        defaultValues: {
            feature1: '',
            feature2: '',
            feature3: '',
            feature4: '',
            feature5: '',
            feature6: '',
            feature7: '',
            feature8: '',
            feature9: '',
            feature10: '',
        },
    })

    useEffect(() => {
        if (setSubmitHandler) {
            setSubmitHandler((values?: DistrictFeatureFormValues) => {
                return new Promise((resolve) => {
                    if (values) {
                        form.reset(values)
                    }

                    form.handleSubmit(
                        (data) => resolve(data),   // ✅ resolve with data
                        () => resolve(null)        // ❌ validation failed
                    )()
                })
            })
        }
    }, [form, setSubmitHandler])

    return (
        <Card className="max-w-3xl mx-auto">
            <CardHeader>
                <CardTitle>District level features</CardTitle>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form onSubmit={onSubmit ? form.handleSubmit(onSubmit) : undefined} className="space-y-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {Array.from({ length: 10 }).map((_, index) => (
                                <FormField
                                    key={index}
                                    control={form.control}
                                    name={`feature${index + 1}` as keyof DistrictFeatureFormValues}
                                    render={({ field }) => (
                                        <FormItem>
                                            <label className="text-sm font-medium">
                                                {featureNames[index] || `Feature ${index + 1}`}
                                            </label>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    placeholder="Enter % change (-100 to 100)"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            ))}
                        </div>
                    </form>
                </Form>
            </CardContent>
        </Card>
    )
}
