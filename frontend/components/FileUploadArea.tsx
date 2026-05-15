'use client';

import { UploadCloud, FileText, Loader2 } from 'lucide-react';
import { useState, useRef } from 'react';

interface FileUploadAreaProps {
  onFilesSelected: (file: File[]) => void;
  isUploading: boolean;
  selectedFileCount?: number;
}

const MAX_FILE_COUNT = 10;
const FILE_LIMIT_MESSAGE = `You can upload a maximum of ${MAX_FILE_COUNT} files. Note: the more files you upload, the lower accuracy may be.`;

export default function FileUploadArea({ onFilesSelected, isUploading, selectedFileCount = 0 }: FileUploadAreaProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFiles = (files: File[]) => {
        if (selectedFileCount + files.length > MAX_FILE_COUNT) {
            setError(FILE_LIMIT_MESSAGE);
            return;
        }

        setError('');
        onFilesSelected(files);
    };

    // Handler for drag and drop
    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
    }

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files).filter(file => 
            file.type === 'application/pdf'
            // file.type === 'text/plain'
            // file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        );
        
        if (files.length > 0) {
            handleFiles(files);
        }
        else {
            // alert('Please upload files in PDF, TXT, or DOCX format.');
            alert('Please upload files in PDF format.');
        }
    };


    // Handler for file selection via file dialog
    const openFileDialog = (accept: string) => {
        if (fileInputRef.current) {
            fileInputRef.current.accept = accept;
            fileInputRef.current.click();
        }
    };

    const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const files = Array.from(e.target.files);
            handleFiles(files);
            e.target.value = '';
        }
    };

    if (isUploading) {
        return (
            <div className="border-2 border-blue-500 bg-blue-50 rounded-2xl p-12 flex flex-col items-center justify-center text-center min-h-[380px]">  
                <Loader2 size={48} className="text-blue-600 animate-spin" />
                <h3 className="text-2xl font-semibold text-gray-900 mt-4">
                    Uploading files...
                </h3>
                <p className="text-gray-500 mt-2">
                    This may take a moment. Please do not refresh the page.
                </p>
            </div>
        );
    }

    return (
        <>
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center text-center transition-all duration-300 min-h-[380px]
                    ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/30'}`}
            >

                <div className={`w-20 h-20 bg-blue-100 rounded-2xl flex items-center justify-center mb-6 transition-transform ${isDragging ? 'scale-110' : ''}`}>
                    <UploadCloud size={40} className="text-blue-600" strokeWidth={2} />
                </div>

                <h2 className="text-2xl font-semibold text-gray-900 mb-3">
                    Drag & drop your files
                </h2>
                {/* <p className="text-gray-500 mb-8 max-w-md">
                    Support for PDF, TXT and DOCX formats
                </p> */}
                <p className="text-gray-500 mb-8 max-w-md">
                    Support only for PDF format
                </p>

                {error && (
                    <div className="mb-6 max-w-md rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                <button
                    // onClick={() => openFileDialog('.pdf,.txt,.docx')}
                    onClick={() => openFileDialog('.pdf')}
                    className="flex items-center gap-2 px-8 py-3.5 bg-white border border-gray-300 hover:border-blue-400 hover:text-blue-600 rounded-2xl text-sm font-medium transition-all active:scale-95"
                >
                    <FileText size={20} />
                    Browse Files
                </button>
            </div>

            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFilesSelected}
                multiple
            />
        </>
    );

}

