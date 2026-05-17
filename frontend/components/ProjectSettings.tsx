'use client';

import { Plus, X, Loader2 } from 'lucide-react';
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
    const [customTags, setCustomTags] = useState<string[]>([]);
    const [isAddingTag, setIsAddingTag] = useState(false);
    const [newTagValue, setNewTagValue] = useState('')

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
        const hasTitle = Boolean(value.title.trim());
        const hasTag = Boolean(value.tag.trim());

        if (!hasTitle && !hasTag) {
            alert('Please enter a project title and select an academic tag before generating summary.');
            return;
        }
        if (!hasTitle) {
            alert('Please enter a project title before generating summary.');
            return;
        }
        if (!hasTag) {
            alert('Please select an academic tag before generating summary.');
            return;
        }

        // Callback to parent to upload file and generate summary
        await onGenerate(value);
    }

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
                            type="button"
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
                                type="button"
                                onClick={addCustomTag}
                                className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full"
                            >
                                <Plus size={16} />
                            </button>
                            <button 
                                type="button"
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
                            type="button"
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
                    type="button"
                    onClick={handleSubmit}
                    // disabled={loading}
                    disabled={disabled}
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
