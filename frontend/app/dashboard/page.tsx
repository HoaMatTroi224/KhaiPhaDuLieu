import ProjectCard from "@/components/ProjectCard";
import Link from "next/link";
import { Plus, Quote } from "lucide-react";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";


export default async function Dashboard() {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
        redirect('/login');
    }
    const userName = user.user_metadata?.full_name?.split(' ')[0] || "Researcher";
    const { data: { session } } = await supabase.auth.getSession();
    const access_token = session?.access_token

    let recentProjects: any[] = [];
    try {
        const res = await fetch('http://localhost:8000/projects/recent', {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${access_token}`
            },
            cache: 'no-store',
        });

        if (res.ok) {
            recentProjects = await res.json();
        }
    } catch (err) {
        console.error("Failed to fetch recent projects:", err);
    } 

    return (
        <div>
            {/* Greeting */}
            <h1 className="text-4xl font-bold mb-8 text-gray-900 tracking-tight">
                Welcome back, <span className="text-blue-600">{userName}</span>!
                {/* Welcome back! */}
            </h1>
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
                {recentProjects.map((project) => (
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

                {/* New Project */}
                {/* <Link href="/projects/new" className="block h-full group">
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
                </Link> */}
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 p-6 rounded-3xl flex flex-col h-[260px] group-hover:shadow-xl group-hover:-translate-y-1 transition-all duration-300">
        
                    <div className="flex-1 flex flex-col justify-center">
                        <div className="text-blue-500 mb-3">
                            <Quote size={28} strokeWidth={2.5} />
                        </div>
                        
                        <p className="text-lg font-medium text-gray-800 leading-snug italic">
                            "The best way to predict the future is to create it."
                        </p>
                        
                        <p className="text-sm text-gray-500 mt-4">- Abraham Lincoln</p>
                    </div>

                    {/* <div className="pt-6 border-t border-blue-100 mt-auto">
                        <div className="flex items-center justify-between text-blue-600 font-semibold">
                            <span className="group-hover:underline">Bắt đầu dự án mới ngay</span>
                            <Plus size={22} className="group-hover:rotate-90 transition-transform" />
                        </div>
                    </div> */}
                </div>
            </div>
        </div>

    );

}