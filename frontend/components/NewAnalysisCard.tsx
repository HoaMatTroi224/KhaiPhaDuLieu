'use client';

import { useEffect, useState } from "react";
import { X, File, Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import FileUploadArea from "./FileUploadArea";
import TextPasteArea from "./TextPasteArea";
import ProjectSettings, { ProjectSettingsData } from "./ProjectSettings";

import { supabase } from '@/lib/supabase/client';

export default function NewAnalysisCard() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const projectId = searchParams?.get('project_id');

    // const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
    // const [isUploading, setIsUploading] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const [projectSettings, setProjectSettings] = useState<ProjectSettingsData>({
        title: "",
        tag: "",
    });

    useEffect(() => {
        if (!projectId) {
            router.push('/');
        }
    }, [projectId, router]);

    const handleSelectedFiles = (files: File[]) => {
        const MAX_SIZE = 10 * 1024 * 1024;  // 10MB
        const validFiles = files.filter(file => {
            // Validate file size
            if (file.size > MAX_SIZE) {
                alert(`${file.name} exceeds 10MB limit`);
                return false;
            }
            // Validate file type
            if (!['application/pdf', 'text/plain'].includes(file.type)) {
                alert(`${file.name} is not PDF or TXT`);
                return false;
            }
            return true;
        });

        setSelectedFiles(prev => [...prev, ...validFiles]);
    };

    // const handleUploadedFiles = (files: File[]) => {
    //     const MAX_SIZE = 50 * 1024 * 1024; // 50MB

    //     const validFiles: File[] = [];
    //     const invalidFiles: string[] = [];

    //     files.forEach(file => {
    //         if (file.size <= MAX_SIZE) {
    //             validFiles.push(file);
    //         } else {
    //             invalidFiles.push(file.name);
    //         }
    //     });

    //     if (invalidFiles.length > 0) {
    //         alert(`The following files exceed the 50MB limit:\n${invalidFiles.join('\n')}`);
    //     }

    //     if (validFiles.length > 0) {
    //         setIsUploading(true);

    //         // Giả lập upload
    //         setTimeout(() => {
    //             setUploadedFiles(prev => [...prev, ...validFiles]);
    //             setIsUploading(false);
    //         }, 1836);
    //     }
    // };

    const removeFile = (index: number) => {
        // setUploadedFiles(prev => prev.filter((_, i) => i !== index));
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    // Main function: Upload Files upto Supabase Storage
    const uploadFileToSupabase = async (file: File, userId: string, projectId: string) => {
        const timestamp = Date.now();
        const randomSuffix = Math.random().toString(36).substring(2, 8);
        const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
        const uniqueName = `${timestamp}_${randomSuffix}_${safeName}`;

        const path = `${userId}/${projectId}/${uniqueName}`;

        const { data: signedData, error: signedError } = await supabase
            .storage.from('documents')
            .createSignedUploadUrl(path);

        if (signedError || !signedData) throw new Error(signedError?.message || 'Failed to get upload URL');

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

    const handleGenerateSummary = async (settings: ProjectSettingsData) => {
        if (!projectId) return alert('Missing project ID');
        if (selectedFiles.length == 0) return alert('Please upload at least one file');
        if (!settings.title?.trim()) return alert('Please enter a project name');

        setIsSubmitting(true);

        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('Not authenticated');

            const uploadedFiles = [];
            for (const file of selectedFiles) {
                const result = await uploadFileToSupabase(file, user.id, projectId);
                uploadedFiles.push({
                    file_name: file.name,
                    file_path: result.path,
                    file_url: result.url,
                    file_type: file.type === 'application/pdf' ? 'pdf' : 'txt',
                    file_size: file.size,
                });
            }

            const { data: { session } } = await supabase.auth.getSession();
            const access_token = session?.access_token

            const response = await fetch(`http://localhost:8000/projects/${projectId}/finalize`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${access_token}`
                },
                body: JSON.stringify({
                    name: settings.title,
                    domain: settings.tag,
                    documents: uploadedFiles,
                }),
            });


            if (!response.ok) {
                // Cleanup files if fail
                await supabase.storage.from('documents').remove(uploadedFiles.map(f => f.file_path));
                throw new Error('Failed to finalize project');
            }

            // const result = await response.json();
            // const documentIds = result.documents.map((doc: any) => doc.id);

            // await fetch(`http://localhost:8000/summaries/generate`, {
            //     method: 'POST',
            //     headers: {
            //         'Content-Type': 'application/json',
            //         'Authorization': `Bearer${access_token}`
            //     },
            //     body: JSON.stringify({
            //         document_ids: documentIds,
            //     })
            // })

            // setProjectSettings(prev => ({
            //     ...prev,
            //     title: settings.title,
            //     tag: settings.tag
            // }))

            // dispatch
            
            router.refresh()
            router.push(`/projects/${projectId}`)
        } catch (error: any) {
            console.error('Error occured while trying to finalize project:', error);
            alert(error.message || 'Failed to finalize project');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!projectId) {
        return (
            <div className="flex item-center justify-center min-h-[400px]">
                <Loader2 className="animate-spin text-blue-600" size={48} />
            </div>
        );
    }


    return (
        <div className="bg-gray-50 rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="p-8">
                <div className="flex flex-col lg:flex-row gap-10">

                    {/* ==================== LEFT SIDE ==================== */}
                    <div className="flex-1">
                        <FileUploadArea 
                            onFilesSelected={handleSelectedFiles} 
                            isUploading={isSubmitting} 
                        />

                        {/* <TextPasteArea /> */}
                    </div>

                    {/* ==================== RIGHT SIDE ==================== */}
                    <div className="flex flex-col gap-6 lg:w-[380px]">
                        
                        <ProjectSettings
                            value={projectSettings}
                            onChange={setProjectSettings}
                            onGenerate={handleGenerateSummary}
                            disabled={isSubmitting}
                        />

                        {/* ==================== CHOSEN FILES ==================== */}
                        <div>
                            <h4 className="text-xs font-medium text-gray-500 mb-3 tracking-widest">
                                CHOSEN FILES
                            </h4>

                            {selectedFiles.length === 0 ? (
                                <div className="text-gray-400 text-sm py-8 text-center border border-dashed border-gray-200 rounded-2xl">
                                    No files chosen yet
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {selectedFiles.map((file, index) => (
                                        <div 
                                            key={index}
                                            className="group flex items-center justify-between bg-white border border-gray-200 hover:border-gray-300 rounded-2xl px-4 py-3 transition-all"
                                        >
                                            <div className="flex items-center gap-3 min-w-0 flex-1">
                                                <div className="w-8 h-8 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                                                    <File size={18} className="text-blue-600" />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <p className="text-sm font-medium text-gray-900 truncate">
                                                        {file.name}
                                                    </p>
                                                    <p className="text-xs text-gray-400">
                                                        {(file.size / (1024 * 1024)).toFixed(1)} MB
                                                    </p>
                                                </div>
                                            </div>

                                            <button
                                                onClick={() => removeFile(index)}
                                                className="text-gray-400 hover:text-blue-500 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-colors"
                                            >
                                                <X size={18} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
}