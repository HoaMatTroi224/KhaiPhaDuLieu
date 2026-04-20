'use client';

import { useState } from "react";
import { X, File } from "lucide-react";
import FileUploadArea from "./FileUploadArea";
import TextPasteArea from "./TextPasteArea";
import ProjectSettings from "./ProjectSettings";

export default function NewAnalysis() {
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
    const[isUploading, setIsUploading] = useState(false);

    const handleUploadedFiles = (files: File[]) => {
        const MAX_SIZE = 50 * 1024 * 1024; // 50MB
        const validFiles: File[] = [];
        const invalidFiles: string[] = [];

        files.forEach(file => {
            if (file.size <= MAX_SIZE) {
                validFiles.push(file);
            } else {
                invalidFiles.push(file.name);
            }
        });

        if (invalidFiles.length > 0) {
            alert(`The following files exceed the 50MB limit:\n${invalidFiles.join('\n')}`);
        }

        if (validFiles.length > 0) {
            setIsUploading(true);

            setTimeout(() => {
                setUploadedFiles(prev => [...prev, ...validFiles]);
                setIsUploading(false);
                alert('Files processed successfully!');
            }, 1836);
        }
    };

    const removeFile = (index: number) => {
        setUploadedFiles(prev => prev.filter((_, i) => i !== index));
    }

    return (
        <div className="bg-gray-50 min-h-screen py-10">
            <div className="max-w-6xl mx-auto px-6">
                <div className="flex flex-col lg:flex-row gap-8">

                    {/* Left Side: File Upload + Text Paste */}
                    <div className="flex-1">

                        <FileUploadArea 
                            onFilesSelected={handleUploadedFiles} 
                            isUploading={isUploading} 
                        />

                        <TextPasteArea />
                    </div>

                    {/* Right Side: Project Settings */}
                    <div className="flex flex-col gap-6 lg:w-[380px]">
                        <ProjectSettings />

                        {/* Uploaded Files List */}
                        <div className="mt-2">
                            <h4 className="text-xs font-medium text-gray-500 mb-3 tracking-widest">
                                CHOSEN FILES
                            </h4>
                        

                            {uploadedFiles.length === 0 ? (
                                <div className="text-gray-400 text-sm py-6 text-center border border-dashed border-gray-200 rounded-2xl">
                                    No files chosen yet
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {uploadedFiles.map((file, index) => (
                                        <div key={index} 
                                            className="flex items-center justify-between bg-white border border-gray-200 rounded-2xl px-4 py-3"
                                        >
                                            <div className="flex items-center gap-3 min-w-0">
                                                <div className="w-8 h-8 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                                                    <File size={16} className="text-blue-600" />
                                                </div>
                                                <div className="min-w-0 flex-1 w-full">
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
                                                className="text-gray-400 hover:text-blue-500 transition-colors"
                                            >
                                                <X size={16} />
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