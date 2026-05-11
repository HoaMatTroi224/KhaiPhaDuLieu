import NewAnalysisCard from "@/components/NewAnalysisCard";
import { Suspense } from "react";

export default function NewProjectPage() {
    return (
        <>
            <div className="mb-10 max-w-2xl mx-auto text-center">
                <h2 className="text-3xl font-semibold text-gray-900 mb-3">
                    Start New Analysis
                </h2>
                <p className="text-gray-500 max-w-2xl">
                    Upload your research papers or paste your notes to begin the synthesis.
                </p>
            </div>
            <Suspense fallback={<div>Im lặng đi Gobi</div>}>
                <NewAnalysisCard />
            </Suspense>
        </>
    );
}