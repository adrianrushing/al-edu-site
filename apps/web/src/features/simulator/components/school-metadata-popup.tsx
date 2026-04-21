import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import type { SchoolSimulationMetadataResponse } from "@/lib/api";

export function SchoolMetadataPopup({
    metadata,
    onClose,
}: {
    metadata: SchoolSimulationMetadataResponse | undefined;
    onClose: () => void;
}) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <Card className="w-full max-w-lg">
                <CardHeader>
                    <CardTitle>School Data Metadata</CardTitle>
                    <CardDescription>
                        Summary of available years and simulation readiness.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <p>Latest year: {metadata?.latest_year ?? "-"}</p>
                    <p>
                        Latest simulatable year:{" "}
                        {metadata?.latest_simulatable_year ?? "-"}
                    </p>
                    <p>Selected year: {metadata?.selected_year ?? "-"}</p>
                    <p>Simulatable: {metadata?.is_simulatable ? "Yes" : "No"}</p>
                    <p>
                        Available years: {metadata?.available_years.join(", ") || "None"}
                    </p>
                    {metadata?.year_status?.length ? (
                        <div className="space-y-1 pt-1 text-xs">
                            {metadata.year_status.map((status) => (
                                <p key={status.year}>
                                    {status.year}:{" "}
                                    {status.is_simulatable ? "Ready" : "Missing data"}
                                </p>
                            ))}
                        </div>
                    ) : null}
                    <Button onClick={onClose} variant="outline">
                        Close
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
