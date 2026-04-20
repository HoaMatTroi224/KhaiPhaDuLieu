'use client';

import ProjectCard from '@/components/ProjectCard';
import CustomSelect from '@/components/CustomSelect'; // Import component mới
import { Filter, ChevronDownCircle } from 'lucide-react';
import { useState } from 'react';

export default function ResearchLibrary() {
    const [discipline, setDiscipline] = useState('All Disciplines');
    const [dateRange, setDateRange] = useState('Last 30 Days');
    const [fileType, setFileType] = useState('All Types');

    const projects = [
        {
            id: 1,
            title: "Neural Pathways in Large Language Model Reasoning",
            description: "An investigative summary regarding the structural similarities between mammalian synaptic...",
            category: "Neuroscience",
            iconName: "Brain",
            createdAt: "Oct 24, 2023",
            categoryColor: 'bg-blue-50 text-blue-600',
            iconColor: 'bg-blue-50 text-blue-600',
        },
        {
            id: 2,
            title: "Post-Scarcity Frameworks in Digital Micro-Economies",
            description: "A comprehensive stitch of three seminal papers regarding the devaluation of digital labor in...",
            category: "Economics",
            iconName: "TrendingUp",
            createdAt: "Oct 19, 2023",
            categoryColor: 'bg-green-50 text-green-600',
            iconColor: 'bg-green-50 text-green-600',
        },
        {
            id: 3,
            title: "Quantum Decoherence Mitigation in Room-Temp Superconductors",
            description: "Synthesized insights from the Seoul Conference. Focuses on the \"Stitch\" between flux pinning an...",
            category: "Quantum Computing",
            iconName: "Atom",
            createdAt: "Oct 12, 2023",
            categoryColor: 'bg-emerald-50 text-emerald-600',
            iconColor: 'bg-emerald-50 text-emerald-600',
        },
        {
            id: 4,
            title: "CRISPR-Cas9 Efficiency in Non-Dividing Neurons",
            description: "A deep dive into cellular repair mechanisms when utilizing specific vector deliveries in the...",
            category: "Biotech",
            iconName: "Dna",
            createdAt: "Sep 30, 2023",
            categoryColor: 'bg-indigo-50 text-indigo-600',
            iconColor: 'bg-indigo-50 text-indigo-600',
        },
        {
            id: 5,
            title: "Epistemological Limits of Synthetic Data Sets",
            description: "Does a model trained purely on model-generated data lead to semantic collapse? An analysis o...",
            category: "Philosophy",
            iconName: "BrainCircuit",
            createdAt: "Sep 24, 2023",
            categoryColor: 'bg-slate-50 text-slate-600',
            iconColor: 'bg-slate-50 text-slate-600',
        },
        {
            id: 6,
            title: "Gravitational Anomaly Mapping in the Orion Nebula",
            description: "Summary of JWST observational data regarding dark matter density fluctuations around proto...",
            category: "Astrophysics",
            iconName: "Telescope",
            createdAt: "Sep 15, 2023",
            categoryColor: 'bg-violet-50 text-violet-600',
            iconColor: 'bg-violet-50 text-violet-600',
        },
    ];

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
                    Research Library
                </h1>
                <p className="text-gray-600 text-lg leading-relaxed max-w-3xl">
                    Manage and explore your digitized academic collection. Your stitched summaries are organized by discipline and date.
                </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 mb-8">
                <CustomSelect
                    label="Discipline"
                    options={['All Disciplines', 'Neuroscience', 'Economics', 'Quantum', 'Biotech', 'Philosophy', 'Astrophysics']}
                    value={discipline}
                    onChange={setDiscipline}
                />

                <CustomSelect
                    label="Date Range"
                    options={['Last 30 Days', 'Last 3 Months', 'Last 6 Months', 'Last Year', 'All Time']}
                    value={dateRange}
                    onChange={setDateRange}
                />

                <CustomSelect
                    label="File Type"
                    options={['All Types', 'PDF', 'TXT', 'DOCX']}
                    value={fileType}
                    onChange={setFileType}
                />

                {/* Filter indicator */}
                <div className="flex items-center gap-2 text-sm text-gray-500 ml-auto">
                    <Filter className="w-4 h-4" />
                    <span>3 filters active</span>
                </div>
            </div>

            {/* Projects Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                {projects.map((project) => (
                    <ProjectCard key={project.id} {...project} />
                ))}
            </div>

            {/* Pagination */}
            <div className="flex flex-col items-center justify-center gap-4">
                <p className="text-sm text-gray-500 font-medium uppercase tracking-wider">
                    Showing 6 of 142 projects
                </p>
                <button className="bg-white border border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold px-6 py-3 rounded-2xl transition-all flex items-center gap-2 group">
                    Load More Projects
                    <ChevronDownCircle className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
                </button>
            </div>
        </div>
    );
}