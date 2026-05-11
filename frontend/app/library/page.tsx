'use client';

import ProjectCard from '@/components/ProjectCard';
import CustomSelect from '@/components/CustomSelect'; 
import { Filter, ChevronDownCircle } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import { supabase } from '@/lib/supabase/client';


export default function ResearchLibrary() {
    const [allProjects, setAllProjects] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    // const [page, setPage] = useState(1);
    // const [total, setTotal] = useState(0);

    // const [discipline, setDiscipline] = useState('All Disciplines');
    // const [dateRange, setDateRange] = useState('Last 30 Days');
    // const [fileType, setFileType] = useState('All Types');

    useEffect(() => {
            const fetchAllProjects = async () => {
            setLoading(true);
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                setLoading(false);
                return;
            }

            try {
                const { data: { session } } = await supabase.auth.getSession();
                const access_token = session?.access_token

                const res = await fetch('http://localhost:8000/projects/', {
                    method: 'GET',
                    headers: {
                        Authorization: `Bearer ${access_token}`
                    },
                    cache: 'no-store',
                });

                if (!res.ok) throw new Error("Failed to fetch all projects")
                const data = await res.json();

                setAllProjects(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to fetch projects");
            } finally {
                setLoading(false);
            }
        };

        fetchAllProjects();
    }, []);

    // const filteredProjects = useMemo(() => {
    //     let res = projects;

    //     if (discipline !== 'All Disciplines') {
    //         res = res.filter(p => p.domain === discipline);
    //     }

    //     if (dateRange !== 'All Time') {
    //         const now = new Date();
    //         const cutoff = new Date();

    //         if (dateRange === 'Last 30 Days') cutoff.setDate(now.getDate() - 30);
    //         else if (dateRange === 'Last 3 Months') cutoff.setMonth(now.getMonth() - 3);
    //         else if (dateRange === 'Last 6 Months') cutoff.setMonth(now.getMonth() - 6);
    //         else if (dateRange === 'Last Year') cutoff.setFullYear(now.getFullYear() - 1);

    //         res = res.filter(p => new Date(p.created_at) >= cutoff);
    //     } 

    //     if (fileType !== 'All Types') {
    //         res = res.filter(p => p.file_type === fileType);
    //     }

    //     return res
    // }, [projects, discipline, dateRange, fileType]);


    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
                    Research Library
                </h1>
                <p className="text-gray-600 text-lg leading-relaxed max-w-3xl">
                    Manage and explore your academic collection.
                </p>
            </div>

            {/* Filters */}
            {/* <div className="flex flex-wrap items-center gap-3 mb-8">
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
                /> */}

                {/* Filter indicator */}
                {/* <div className="flex items-center gap-2 text-sm text-gray-500 ml-auto">
                    <Filter className="w-4 h-4" />
                    <span>3 filters active</span>
                </div>
            </div> */}

            {/* Projects Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                {allProjects.map((project) => (
                    <ProjectCard 
                        key={project.id} 
                        id={project.id}
                        title={project.name}
                        description={project.description}
                        category={project.domain}
                        createdAt={project.created_at}
                        // {...project} 
                    />
                ))}
            </div>

            {/* Pagination */}
            {/* <div className="flex flex-col items-center justify-center gap-4">
                <p className="text-sm text-gray-500 font-medium uppercase tracking-wider">
                    Showing 6 of 142 projects
                </p>
                <button className="bg-white border border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold px-6 py-3 rounded-2xl transition-all flex items-center gap-2 group">
                    Load More Projects
                    <ChevronDownCircle className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
                </button>
            </div> */}
        </div>
    );
}