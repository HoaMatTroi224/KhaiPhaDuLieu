'use client';

import { useState, useEffect } from 'react';
import { FilePen } from "lucide-react";
import { useAuth } from '@/lib/hooks/useAuth';

// Mock data
// const documents = [
//     { id: 1, name: "Trứng rán cần mỡ.pdf", active: true },
//     { id: 2, name: "Bắp cần bơ.docx", active: false },
//     { id: 3, name: "Yêu không cần cớ.txt", active: false },
// ];
// type Document = { id: string; name: string};

type DocumentListItem = {
    id: string;
    title?: string | null;
    file_name?: string | null;
    status?: 'uploaded' | 'processing' | 'indexed' | 'failed';
};

export default function DocumentList({
    projectId,
    selectedDocId,
    onSelectedDoc
}: {
    projectId: string;
    selectedDocId: string | null;
    onSelectedDoc: (doc: DocumentListItem) => void;
}) {
    const [documents, setDocuments] = useState<DocumentListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const { token, loading: authLoading } = useAuth();

    useEffect(() => {
        if (!projectId || !token || authLoading) return;

        let isMounted = true;
        let refreshTimer: ReturnType<typeof setTimeout> | null = null;
        const REFRESH_DELAY_MS = 5_000;

        const fetchDocs = async () => {
            try {

                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/documents/?project_id=${projectId}`, {
                    method: 'GET',
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                if (!res.ok) throw new Error('Failed to fetch documents');
                const data = await res.json() as DocumentListItem[];
                if (!isMounted) return;

                setDocuments(data);

                const hasPendingMetadata = data.some((doc) =>
                    doc.status === 'uploaded' ||
                    doc.status === 'processing' ||
                    !doc.title?.trim()
                );
                if (hasPendingMetadata) {
                    refreshTimer = setTimeout(fetchDocs, REFRESH_DELAY_MS);
                }
            } catch (err) {
                console.error(err);
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };
        fetchDocs();

        return () => {
            isMounted = false;
            if (refreshTimer) clearTimeout(refreshTimer);
        };
    }, [projectId, token, authLoading]);

    useEffect(() => {
        if (!selectedDocId && documents.length > 0) {
            onSelectedDoc(documents[0]);
        }
    }, [documents, selectedDocId, onSelectedDoc]);

    useEffect(() => {
        if (!selectedDocId) return;

        const currentDoc = documents.find((doc) => doc.id === selectedDocId);
        if (currentDoc) {
            onSelectedDoc(currentDoc);
        }
    }, [documents, selectedDocId, onSelectedDoc]);

    if (authLoading || loading) return <div className="p-6 text-sm text-gray-500">Loading documents...</div>;

    return (
        <div className="p-6">
            <div className="uppercase text-xs font-semibold text-gray-400 tracking-widest mb-4">
                Documents
            </div>

            <div className="space-y-1">
                {documents.map((doc) => (
                    <div 
                        key={doc.id} 
                        onClick={() => onSelectedDoc(doc)}
                        // className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl cursor-pointer transition
                        //     ${doc.active
                        //         ? 'bg-blue-50 text-blue-700'
                        //         : 'text-gray-600 hover:bg-gray-100'
                        //     }`
                        // }
                        className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl cursor-pointer transition
                            ${selectedDocId === doc.id ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
                    >

                        <div className='flex-shrink-0'>
                            <FilePen size={16} />
                        </div>

                        <div className="flex-1 min-w-0 overflow-hidden">
                            <p className="text-sm truncate font-medium">
                                {doc.title?.trim() || doc.file_name}
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
            {/* <div className="p-6 pt-4 border-t border-gray-100 ">
                <button className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-gray-300 shadow-sm text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition">
                    <PlusCircle size={16} />
                    Add Document
                </button>
            </div> */}


            {/* Add Document Button */}
            {/* <button className="mt-8 w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-dashed border-gray-200 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition">
                <PlusCircle size={16} />
                Add Document
            </button> */}

        </div>
    );
}
