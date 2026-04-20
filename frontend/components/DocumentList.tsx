'use client';

import { FilePen, BookOpenText, PlusCircle } from "lucide-react";

// Mock data
const documents = [
    { id: 1, name: "Trứng rán cần mỡ.pdf", active: true },
    { id: 2, name: "Bắp cần bơ.docx", active: false },
    { id: 3, name: "Yêu không cần cớ.txt", active: false },
];
export default function DocumentList() {
    return (
        <div className="p-6">
            <div className="uppercase text-xs font-semibold text-gray-400 tracking-widest mb-4">
                Documents
            </div>

            <div className="space-y-1">
                {documents.map((doc) => (
                    <div 
                        key={doc.id} 
                        className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl cursor-pointer transition
                            ${doc.active
                                ? 'bg-blue-50 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-100'
                            }`}
                    >
                        <FilePen size={16} />

                        <div className="flex-1 min-w0">
                            <p className="text-sm truncate font-medium">
                                {doc.name}
                            </p>
                        </div>
                        {/* <div className="w-8 h-8 flex items-center justify-center text-gray-500">
                            {doc.active ? <BookOpenText size={16} /> : <FilePen size={16} />}
                        </div>

                        <div className="flex-1 min-w-0">
                            <p className={`text-sm truncate
                                ${doc.active ? 'font-semibold text-blue-700' : 'text-gray-700'}`}
                            >
                                {doc.name}
                            </p>
                        </div> */}
                    </div>
                ))}
            </div>

            {/* Divider + Add Document Button */}
            <div className="p-6 pt-4 border-t border-gray-100 ">
                <button className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-gray-300 shadow-sm text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition">
                    <PlusCircle size={16} />
                    Add Document
                </button>
            </div>


            {/* Add Document Button */}
            {/* <button className="mt-8 w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-dashed border-gray-200 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition">
                <PlusCircle size={16} />
                Add Document
            </button> */}

        </div>
    );
}