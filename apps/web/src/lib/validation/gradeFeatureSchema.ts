import { z } from 'zod'

export const GradeFeatureSchema = z.object({
    feature1: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature2: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
})

export type GradeFeatureFormValues = z.infer<typeof GradeFeatureSchema>
