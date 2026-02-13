"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { useEffect } from "react";

export default function FeatureAdjustmentForm({ setSubmitHandler }) {
  const [districtFeatures, setDistrictFeatures] = useState(Array(10).fill(""))
  const [gradeFeatures, setGradeFeatures] = useState(Array(2).fill(""))

  const handleInputChange = (group, index, value) => {
    const updater = group === "district" ? setDistrictFeatures : setGradeFeatures
    const data = group === "district" ? [...districtFeatures] : [...gradeFeatures]
    data[index] = value
    updater(data)
  }

  const handleAdjustClick = () => {
    // TODO: Navigate to adjusted results page or call dummy API
    console.log("Adjusted Features:", { districtFeatures, gradeFeatures })
  }

  // inside the component
  useEffect(() => {
    if (setSubmitHandler) {
      setSubmitHandler(() => form.handleSubmit(onSubmit));
    }
  }, [form, setSubmitHandler]);

  return (
    <Card className="w-full max-w-2xl mx-auto my-8">
      <CardHeader>
        <CardTitle>Adjust District Features</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h3 className="font-semibold mb-2">District-Level Features</h3>
          <div className="grid grid-cols-2 gap-4">
            {districtFeatures.map((val, i) => (
              <Input
                key={`district-${i}`}
                type="number"
                placeholder={`Feature ${i + 1}`}
                value={val}
                onChange={(e) => handleInputChange("district", i, e.target.value)}
              />
            ))}
          </div>
        </div>
        <div>
          <h3 className="font-semibold mb-2">Grade-Level Features</h3>
          <div className="grid grid-cols-2 gap-4">
            {gradeFeatures.map((val, i) => (
              <Input
                key={`grade-${i}`}
                type="number"
                placeholder={`Grade Feature ${i + 1}`}
                value={val}
                onChange={(e) => handleInputChange("grade", i, e.target.value)}
              />
            ))}
          </div>
        </div>
        <Button className="mt-4 w-full" onClick={handleAdjustClick}>
          Apply Adjustments
        </Button>
      </CardContent>
    </Card>
  )
}
