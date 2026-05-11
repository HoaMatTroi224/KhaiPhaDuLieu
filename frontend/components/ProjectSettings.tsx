'use client';

import { supabase } from '@/lib/supabase/client';
import { Plus, X, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

const DEFAULT_TAGS = [
    'Mathematics', 'Technology', 'Physics', 'Chemistry', 'Biology', 
    'Geography', 'History'  
]

export interface ProjectSettingsData {
    title: string;
    tag: string;
}

interface ProjectSettingsProps {
    value: ProjectSettingsData;
    onChange: (value: ProjectSettingsData) => void;
    onGenerate: (settings: ProjectSettingsData) => Promise<void>;
    disabled?: boolean
}

export default function ProjectSettings({value, onChange, onGenerate, disabled = false}: ProjectSettingsProps) {
    const router = useRouter();
    const [selectedTag, setSelectedTag] = useState<string>();
    const [projectTitle, setProjectTitle] = useState('');
    const [customTags, setCustomTags] = useState<string[]>([]);
    const [isAddingTag, setIsAddingTag] = useState(false);
    const [newTagValue, setNewTagValue] = useState('')
    const [loading, setLoading] = useState(false);

    const allTags = [...DEFAULT_TAGS, ...customTags];
    
    const toggleTag = (tag: string) => {
        // setSelectedTag(prev => (prev === tag ? '' : tag));
        const newTag = value.tag === tag ? '' : tag;
        onChange({ ...value, tag: newTag })
    };

    const addCustomTag = () => {
        const trimmed = newTagValue.trim();
        if (trimmed && !allTags.includes(trimmed)) {
            setCustomTags(prev => [...prev, trimmed]);
            // setSelectedTag(trimmed);
            onChange({ ...value, tag: trimmed });
        }
        setNewTagValue('');
        setIsAddingTag(false);
    }

    const handleSubmit = async () => {
        if (!value.title.trim()) {
            alert('Please enter a project title');
            return;
        }
        if (!value.tag) {
            alert('Please select an academic tag');
            return;
        }

        // Callback to parent to upload file and generate summary
        await onGenerate(value);
    }

    // const handleGenerateSummary = async () => {
    //     if (!projectTitle.trim()) {
    //         alert('Please enter a project title');
    //         return;
    //     }
    //     if (!selectedTag) {
    //         alert('Please select a academic tag');
    //         return;
    //     }
    //     setLoading(true);
    //     try {
    //         const { data: { session } } = await supabase.auth.getSession();
    //         const token = session?.access_token;
    //         if (!token) throw new Error('Not authenticated');

    //         const formData = new FormData();
    //         formData.append('name', projectTitle);
    //         formData.append('domain', selectedTag);
    //         formData.append('description', '');

    //         const res = await fetch(``, {
    //             method: 'POST',
    //             headers: { Authorization: `Bearer ${token}` },
    //             body: formData,
    //         });
    //         if (!res.ok) throw new Error('Failed to create project');
    //         const project = await res.json();
    //         router.push(`/project/${project.id}`);
    //     } catch (err: any) {
    //         alert(err.message);
    //     } finally {
    //         setLoading(false);
    //     }
    // }

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
                    value={value.title}
                    onChange={(e) => onChange({ ...value, title: e.target.value })}
                    className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:border-blue-500 text-gray-900 placeholder:text-gray-400"
                />
            </div>

            {/* Academic Tags */}
            <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    ACADEMIC TAGS
                </label>
                <div className="flex flex-wrap gap-2">
                    {allTags.map(tag => (
                        <button 
                            key={tag}
                            onClick={() => toggleTag(tag)}
                            className={`px-4 py-2 text-sm rounded-2xl transition-colors ${
                                // selectedTag === tag ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                value.tag === tag ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                        >
                            {tag}
                        </button>
                    ))}
                    {isAddingTag ? (
                        <div className="flex items-center gap-1">
                            <input
                                type="text"
                                value={newTagValue}
                                onChange={e => setNewTagValue(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === "Enter") addCustomTag();
                                    if (e.key === "Escape") {
                                        setNewTagValue('');
                                        setIsAddingTag(false);
                                    }
                                }}
                                placeholder="New tag..."
                                className="w-28 px-3 py-1.5 text-sm border border-gray-300 rounded-2xl focus:outline-none focus:border-blue-400"
                                autoFocus
                            />
                            <button 
                                onClick={addCustomTag}
                                className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full"
                            >
                                <Plus size={16} />
                            </button>
                            <button 
                                onClick={() => {
                                    setNewTagValue('');
                                    setIsAddingTag(false);
                                }}
                                className='p-1.5 text-gray-400 hover:bg-gray-100 rounded-full'
                            >   
                                <X size={16} />
                            </button>
                        </div>
                    ) : (
                        <button 
                            onClick={() => setIsAddingTag(true)}
                            className="flex items-center gap-1 px-4 py-2 bg-white border border-dashed border-gray-400 hover:border-blue-400 text-gray-500 hover:text-blue-500 text-sm rounded-2xl transition-colors"
                        >
                            <Plus size={16} />
                            Add
                        </button>

                    )}
                </div>
            </div>

            {/* Generate Button */}
            <div className="mt-auto">
                <button 
                    onClick={handleSubmit}
                    // disabled={loading}
                    disabled={disabled || !value.title.trim() || !value.tag}
                    className="w-full flex items-center justify-center gap-2 px-5 py-4 bg-blue-600 text-white text-base font-medium rounded-2xl hover:bg-blue-700 transition-colors"
                >
                    {/* {loading ? <Loader2 className="animate-spin" size={20} /> : null} */}
                    {/* {loading ? 'Creating...' : 'Generate Summary'} */}
                    {disabled ? <Loader2 className="animate-spin" size={20} /> : null}
                    {disabled ? 'Creating...' : 'Generate Summary'}
                </button>
            </div>
        </div>


    );
}
