import ProjectCard from "@/components/ProjectCard";
import Link from "next/link";
import { Plus } from "lucide-react";


export default function Dashboard() {
    // Mock data
    const projects = [
        {
            id: 1,
            title: "Neural Correlates of Deep Learning Models",
            description: "This research explores the intersection between biological neural networks and artificial intelligence systems...",
            category: "Neuroscience",
            iconName: "Brain",
            createdAt: "24/03/2026",
            categoryColor: 'bg-green-100 text-green-600',
            iconColor: 'bg-green-100 text-green-600',
        },
        {
            id: 2,
            title: "Quantum Entanglement in Micro-Scale Oscillators",
            description: "Experimental verification of macroscopic quantum states through optomechanical systems...",
            category: "Physics",
            iconName: "Atom",
            createdAt: "24/03/2026",
            categoryColor: 'bg-purple-100 text-purple-600',
            iconColor: 'bg-purple-100 text-purple-600',
        },
    ];

    return (
        <div>
            {/* Greeting */}
            <h1 className="text-4xl font-bold mb-8 text-gray-900 tracking-tight">Welcome back, Ánh!</h1>
            <p className="text-gray-600">
                <span className="italic">"Where ideas meet,</span>
                <span className="font-bold"> where dreams become reality."</span>
            </p>

            <div className="border-t border-gray-100 my-10" />

            {/* Statistics */}

            {/* Recent Projects */}
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-semibold text-gray-900 tracking-tight">
                    Recent Projects
                </h2>

                <Link href="/library" className="text-sm text-blue-600 cursor-pointer hover:underline">
                    <span>View All →</span>
                </Link>
                {/* <span className="text-sm text-blue-600 cursor-pointer hover:underline">
                    View All →
                </span> */}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map((project) => (
                    <ProjectCard key={project.id} {...project} />
                ))}

                {/* New Project */}
                <Link href="/projects/new" className="block h-full group">
                    <div className="bg-transparent border-2 border-dashed border-gray-200 p-6 rounded-3xl flex flex-col items-center justify-center text-center h-[260px] group-hover:bg-blue-50/30 group-hover:border-blue-300 transition-all duration-300">
                        <div className="w-12 h-12 bg-gray-300 text-white rounded-full flex items-center justify-center mb-4 group-hover:bg-blue-500 group-hover:scale-110 transition-all duration-300">
                            <Plus size={24} strokeWidth={3} />
                        </div>
                        <h3 className="font-semibold text-[17px] text-gray-900 mb-2">
                            Create New Project
                        </h3>
                        <span className="text-blue-600 font-semibold text-sm group-hover:underline">
                            Start Research
                        </span>
                    </div>
                </Link>
            </div>
        </div>

    );

}