'use client';
import Link from 'next/link';
import * as Icons from 'lucide-react';

interface ProjectCardProps {
    id: number;
    title: string;
    description: string;
    category: string;
    iconName: string;
    createdAt: string;
    categoryColor?: string;
    iconColor?: string;
}

export default function ProjectCard({ id, title, description, category, iconName, createdAt, categoryColor, iconColor }: ProjectCardProps) {
    const Icon = (Icons[iconName as keyof typeof Icons] || Icons.FileText) as React.ElementType;

    return (
        <Link href={`/projects/${id}`} className="block h-full group">
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-pointer group">
                {/* Header: Icon + Category + Title + Description */}
                <div className="flex items-start justify-between mb-3">
                    <div className={`p-2.5 rounded-xl transition-transform group-hover:scale-110 ${iconColor}`}>
                        <Icon size={18} />
                    </div>
                    <span className={`text-[10px] font-bold px-3 py-1.5 rounded-full uppercase tracking-wider ${categoryColor}`}>
                        {category}
                    </span>
                </div>
                <h3 className="font-bold text-lg leading-snug mb-2 text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                    {title}
                </h3>
                <p className="text-gray-500 text-sm italic line-clamp-3">
                    {description}
                </p>

        
                {/* Footer: Date + Open */}
                <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-50">
                    <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider">
                        {createdAt}
                    </span>
                    <span className="bg-gray-50 group-hover:bg-blue-600 group-hover:text-white text-gray-600 px-4 py-2 rounded-full text-xs font-semibold transition-colors">
                        Open 
                    </span>
                </div>
            </div>
        </Link>
    );
}