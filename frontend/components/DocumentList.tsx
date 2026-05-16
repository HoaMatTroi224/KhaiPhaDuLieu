'use client';

import { useCallback, useEffect, useState } from 'react';
import { File, FilePen, Loader2, PlusCircle, X } from "lucide-react";
import { useAuth } from '@/lib/hooks/useAuth';
import { supabase } from '@/lib/supabase/client';
import FileUploadArea from './FileUploadArea';

const MAX_DOCUMENT_COUNT = 10;

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
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const { token, loading: authLoading } = useAuth();

    const fetchDocs = useCallback(async () => {
        if (!projectId || !token) return [];

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/documents/?project_id=${projectId}`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        if (!res.ok) throw new Error('Failed to fetch documents');
        const data = await res.json() as DocumentListItem[];
        setDocuments(data);
        return data;
    }, [projectId, token]);

    useEffect(() => {
        if (!projectId || !token || authLoading) return;
        let isMounted = true;
        let refreshTimer: ReturnType<typeof setTimeout> | null = null;
        const REFRESH_DELAY_MS = 5_000;

        const refreshDocs = async () => {
            try {
                const data = await fetchDocs();
                if (!isMounted) return;

                const hasPendingMetadata = data.some((doc) =>
                    doc.status === 'uploaded' ||
                    doc.status === 'processing' ||
                    !doc.title?.trim()
                );
                if (hasPendingMetadata) {
                    refreshTimer = setTimeout(refreshDocs, REFRESH_DELAY_MS);
                }
            } catch (err) {
                console.error(err);
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };
        refreshDocs();

        return () => {
            isMounted = false;
            if (refreshTimer) clearTimeout(refreshTimer);
        };
    }, [projectId, token, authLoading, fetchDocs, refreshKey]);

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

    const handleSelectedFiles = (files: File[]) => {
        const MAX_SIZE = 10 * 1024 * 1024;
        const remainingSlots = MAX_DOCUMENT_COUNT - documents.length - selectedFiles.length;

        if (remainingSlots <= 0) {
            alert(`This project already has the maximum of ${MAX_DOCUMENT_COUNT} documents.`);
            return;
        }

        const validFiles = files.filter(file => {
            if (file.size > MAX_SIZE) {
                alert(`${file.name} exceeds 10MB limit`);
                return false;
            }
            if (file.type !== 'application/pdf') {
                alert(`${file.name} is not PDF`);
                return false;
            }
            return true;
        }).slice(0, remainingSlots);

        if (files.length > remainingSlots) {
            alert(`You can add ${remainingSlots} more document${remainingSlots === 1 ? '' : 's'} to this project.`);
        }

        setSelectedFiles(prev => [...prev, ...validFiles]);
    };

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, fileIndex) => fileIndex !== index));
    };

    const uploadFileToSupabase = async (file: File, userId: string) => {
        const timestamp = Date.now();
        const randomSuffix = Math.random().toString(36).substring(2, 8);
        const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
        const uniqueName = `${timestamp}_${randomSuffix}_${safeName}`;
        const path = `${userId}/${projectId}/${uniqueName}`;

        const { data: signedData, error: signedError } = await supabase
            .storage.from('documents')
            .createSignedUploadUrl(path);

        if (signedError || !signedData) {
            throw new Error(signedError?.message || 'Failed to get upload URL');
        }

        const { error: uploadError } = await supabase
            .storage.from('documents')
            .uploadToSignedUrl(signedData.path, signedData.token, file, {
                contentType: file.type,
                cacheControl: '3600',
                upsert: false
            });

        if (uploadError) throw new Error(uploadError.message);

        const { data: { publicUrl } } = supabase
            .storage.from('documents')
            .getPublicUrl(signedData.path);

        return { path: signedData.path, url: publicUrl };
    };

    const handleAddDocuments = async () => {
        if (!projectId || !token) return;
        if (selectedFiles.length === 0) {
            alert('Please upload at least one file');
            return;
        }

        setIsSubmitting(true);
        const uploadedFiles: { file_path: string }[] = [];

        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('Not authenticated');

            const documentPayload = [];
            for (const file of selectedFiles) {
                const uploadResult = await uploadFileToSupabase(file, user.id);
                uploadedFiles.push({ file_path: uploadResult.path });
                documentPayload.push({
                    file_name: file.name,
                    file_path: uploadResult.path,
                    file_url: uploadResult.url,
                    file_type: 'pdf',
                    file_size: file.size,
                });
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/documents/?project_id=${projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ documents: documentPayload }),
            });

            if (!response.ok) {
                await supabase.storage.from('documents').remove(uploadedFiles.map(file => file.file_path));
                throw new Error('Failed to add documents');
            }

            const addedDocs = await response.json() as DocumentListItem[];
            setSelectedFiles([]);
            setIsModalOpen(false);
            const data = await fetchDocs();
            setRefreshKey(prev => prev + 1);
            onSelectedDoc(addedDocs[0] || data[0]);
        } catch (error) {
            console.error('Error occured while trying to add documents:', error);
            alert(error instanceof Error ? error.message : 'Failed to add documents');
        } finally {
            setIsSubmitting(false);
        }
    };

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
                    </div>
                ))}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100">
                <button
                    onClick={() => setIsModalOpen(true)}
                    disabled={documents.length >= MAX_DOCUMENT_COUNT}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-gray-300 shadow-sm text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition"
                >
                    <PlusCircle size={16} />
                    Add Documents
                </button>
            </div>

            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
                    <div className="w-full max-w-4xl rounded-2xl bg-white shadow-xl">
                        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                            <h3 className="text-lg font-semibold text-gray-900">Add Documents</h3>
                            <button
                                onClick={() => {
                                    if (isSubmitting) return;
                                    setIsModalOpen(false);
                                }}
                                className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_280px]">
                            <FileUploadArea
                                onFilesSelected={handleSelectedFiles}
                                isUploading={isSubmitting}
                                selectedFileCount={documents.length + selectedFiles.length}
                            />

                            <div className="flex min-h-[380px] flex-col">
                                <div className="mb-3 text-xs font-medium tracking-widest text-gray-500">
                                    CHOSEN FILES
                                </div>

                                <div className="flex-1 space-y-2 overflow-y-auto">
                                    {selectedFiles.length === 0 ? (
                                        <div className="rounded-2xl border border-dashed border-gray-200 py-8 text-center text-sm text-gray-400">
                                            No files chosen yet
                                        </div>
                                    ) : (
                                        selectedFiles.map((file, index) => (
                                            <div
                                                key={`${file.name}-${index}`}
                                                className="flex items-center justify-between rounded-2xl border border-gray-200 px-4 py-3"
                                            >
                                                <div className="flex min-w-0 items-center gap-3">
                                                    <File size={18} className="shrink-0 text-blue-600" />
                                                    <div className="min-w-0">
                                                        <p className="truncate text-sm font-medium text-gray-900">{file.name}</p>
                                                        <p className="text-xs text-gray-400">
                                                            {(file.size / (1024 * 1024)).toFixed(1)} MB
                                                        </p>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => removeFile(index)}
                                                    disabled={isSubmitting}
                                                    className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 disabled:opacity-50"
                                                >
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>

                                <button
                                    onClick={handleAddDocuments}
                                    disabled={selectedFiles.length === 0 || isSubmitting}
                                    className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                                    Add Documents
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
