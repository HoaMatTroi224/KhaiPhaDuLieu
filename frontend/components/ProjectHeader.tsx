'use client';

import { ArrowLeft, Pencil, Share2, Save } from "lucide-react";
import Link from "next/link";

interface ProjectHeaderProps {
    title?: string;
}

export default function ProjectHeader({ title = "Untitled Project" }: ProjectHeaderProps) {
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

            {/* Right: Placeholder for future actions */}
            {/* <div className="flex items-center gap-3"> */}
                {/* Future action buttons can go here */}
                
                {/* <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-2xl transition-colors">
                    <Share2 size={18} />
                    Share
                </button>

                <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-2xl transition-colors">
                    <Save size={18} />
                    Save
                </button>

                <Link href="/projects/new">
                    <button className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-full shadow-sm">
                        New Project
                    </button>
                </Link>

            </div> */}
        </div>
    );
}