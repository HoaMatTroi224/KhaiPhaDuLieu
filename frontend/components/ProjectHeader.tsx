'use client';

import { ArrowLeft, Download, Pencil } from "lucide-react";
import Link from "next/link";

interface ProjectHeaderProps {
    title?: string;
    canDownloadSummary?: boolean;
    onDownloadSummary?: () => void;
}

export default function ProjectHeader({
    title = "Untitled Project",
    canDownloadSummary = false,
    onDownloadSummary,
}: ProjectHeaderProps) {
    return (
        <div className="h-[60px] border-b border-gray-200 bg-white px-8 flex items-center justify-between sticky top-0 z-50">
            
            {/* Left: Back Button + Project Title */}
            <div className="flex items-center gap-4">
                <Link href="/library" className="text-gray-500 hover:text-gray-700 transition-colors">
                    <ArrowLeft size={22} />
                </Link>

                <div className="flex items-center gap-3">
                    <h1 className="text-lg font-semibold text-gray-900 truncate max-w-md">
                        {title}
                    </h1>
                    <Pencil size={16} className="text-gray-400 cursor-pointer hover:text-blue-700 transition-colors" />
                </div>
            </div>

            {/* Center: File Type Tabs */}
            {/* <div className="flex items-center bg-gray-100 p-1 rounded-full">
                <button className="px-4 py-1.5 text-sm font-medium rounded-full bg-white text-blue-600 shadow-sm">
                    PDF
                </button>
                <button className="px-4 py-1.5 text-sm font-medium text-gray-500">
                    TXT
                </button>
            </div> */}

            <div className="flex items-center gap-3">
                <button
                    onClick={onDownloadSummary}
                    disabled={!canDownloadSummary}
                    title={canDownloadSummary ? "Download summary" : "Select a loaded summary first"}
                    className="flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-green-100 hover:text-green-800 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
                >
                    <Download size={18} />
                    Download
                </button>
            </div>
        </div>
    );
}
