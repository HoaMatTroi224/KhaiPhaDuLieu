'use client';

import { Clipboard } from "lucide-react";

export default function TextPasteArea() {
    return (
        <div className="mt-6 bg-gray-100 border border-gray-100 rounded-3xl p-6">
            <div className="flex items-center gap-2 text-sm text-gray-700 mb-3">    
                <Clipboard size={18} className="text-blue-700"/>
                <span className="font-semibold">Or paste raw text</span>
            </div>
            <textarea
                placeholder="Paste your research notes or abstract here..."
                className="w-full h-40 resize-y min-h-[140px] bg-white border border-gray-200 focus:border-blue-400 rounded-2xl px-5 py-4 text-sm text-gray-900 focus:outline-none transition-colors"
                rows={6}
            />
        </div>
    );
}