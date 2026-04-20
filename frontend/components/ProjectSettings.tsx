'use client';

import { Plus } from 'lucide-react';
import Link from 'next/link';

export default function ProjectSettings() {
    return (
        <div className="w-full lg:w-[380px] flex flex-col gap-6">
            {/* Project Title */}
            <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    PROJECT TITLE
                </label>
                <input
                    type="text"
                    placeholder="Enter project title"
                    className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:border-blue-500 text-gray-900 placeholder:text-gray-400"
                />
            </div>

            {/* Academic Tags */}
            <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    ACADEMIC TAGS
                </label>
                <div className="flex flex-wrap gap-2">
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Maths</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Physics</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Chemistry</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Technology</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Biology</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">History</div>
                    <div className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-2xl">Geography</div>
                    <button className="flex items-center gap-1 px-4 py-2 bg-white border border-dashed border-gray-400 hover:border-blue-400 text-gray-500 hover:text-blue-500 text-sm rounded-2xl transition-colors">
                        <Plus size={16} />
                        Add
                    </button>
                </div>
            </div>

            {/* Generate Button */}
            <div className="mt-auto">
                <Link href="/projects/new" className="block">
                    <button className="w-full flex items-center justify-center gap-2 px-5 py-4 bg-blue-600 text-white text-base font-medium rounded-2xl hover:bg-blue-700 transition-colors">
                        Generate Summary
                    </button>
                </Link>
            </div>
        </div>


    );
}
