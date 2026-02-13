import { z } from 'zod'

export const DistrictFeatureSchema = z.object({
    feature1: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature2: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature3: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature4: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature5: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature6: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature7: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature8: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature9: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
    feature10: z
        .string()
        .min(1, { message: 'This field is required.' })
        .refine((val) => !isNaN(Number(val)), { message: 'Must be a number' }),
})

export type DistrictFeatureFormValues = z.infer<typeof DistrictFeatureSchema>
