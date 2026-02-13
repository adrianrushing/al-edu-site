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
import { GradeFeatureSchema, type GradeFeatureFormValues } from '@/lib/validation/gradeFeatureSchema'
import { useEffect } from 'react'

interface GradeFeatureFormProps {
    setSubmitHandler?: (handler: (values?: GradeFeatureFormValues) => Promise<GradeFeatureFormValues | null>) => void
    onSubmit?: (values: GradeFeatureFormValues) => void
    featureNames?: string[]
}

export function GradeFeatureForm({ setSubmitHandler, onSubmit, featureNames = [] }: GradeFeatureFormProps) {
    const form = useForm<GradeFeatureFormValues>({
        resolver: zodResolver(GradeFeatureSchema),
        defaultValues: {
            feature1: '',
            feature2: '',
        },
    })

    useEffect(() => {
        if (setSubmitHandler) {
            setSubmitHandler((values?: GradeFeatureFormValues) => {
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
                <CardTitle>Grade level features</CardTitle>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form onSubmit={onSubmit ? form.handleSubmit(onSubmit) : undefined} className="space-y-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {Array.from({ length: 2 }).map((_, index) => (
                                <FormField
                                    key={index}
                                    control={form.control}
                                    name={`feature${index + 1}` as keyof GradeFeatureFormValues}
                                    render={({ field }) => (
                                        <FormItem>
                                            <label className="text-sm font-medium mb-1 block">
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
