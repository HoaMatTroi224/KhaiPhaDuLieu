'use client';
import Link from 'next/link';
import { Plus, User, Settings, LogOut, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import type { User as SupabaseUser } from '@supabase/supabase-js';

export default function TopNav() {
    const router = useRouter();
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [user, setUser] = useState<SupabaseUser | null>(null);
    const [isCreatingProject, setIsCreatingProject] = useState(false);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setDropdownOpen(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    useEffect(() => {
        const fetchUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            setUser(user);
        };

        fetchUser();

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null)
        })

        return () => subscription.unsubscribe()
    }, []);

    const handleLogout = async () => {
        await supabase.auth.signOut();
        window.location.href = '/auth/login'; // Redirect to login page after logout
    };

    const handleCreateProject = async (event: React.MouseEvent) => {
        event.preventDefault(); 

        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
            window.location.href = '/auth/login';
            return;
        }

        setIsCreatingProject(true);

        const { data: { session } } = await supabase.auth.getSession();
        const access_token = session?.access_token

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects/initialize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${access_token}`,
                },
            });
            
            if (!response.ok) throw new Error("Failed to initialize project");

            const data = await response.json();
            const projectId = data.id
            
            router.push(`/projects/new?project_id=${projectId}`);
        } catch (error: unknown) {
            console.log('Error occured while trying to initialize project:', error);
            alert(error instanceof Error ? error.message : 'Failed to initialize project');
        } finally {
            setIsCreatingProject(false);
        }
    }

    return (
        <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
            {/* Left: Logo + Search */}
            <div className="flex items-center gap-8">
                {/* Logo */}
                <Link
                    href="/dashboard"
                    aria-label="Go to dashboard"
                    className="flex items-center gap-3 rounded-2xl transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                    <div className="w-9 h-9 bg-blue-600 rounded-2xl flex items-center justify-center text-white font-bold text-3xl leading-none">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 3V4M12 20V21M4 12H3M6.5 6.5L5.5 5.5M17.5 6.5L18.5 5.5M21 12H20M12 7C9.23858 7 7 9.23858 7 12C7 13.5 7.5 15 8.5 16C9 16.5 9.5 17 9.5 18H14.5C14.5 17 15 16.5 15.5 16C16.5 15 17 13.5 17 12C17 9.23858 14.7614 7 12 7Z"
                            stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                            <path d="M9.5 19H14.5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>    
                    </div>
                    <span className="font-semibold text-3xl tracking-tighter text-gray-900">Lumen</span>
                </Link>

                {/* Search Bar */}
                {/* <div className="relative w-[420px]">
                    <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                        <Search size={18} />
                    </div>
                    <input
                        type="text"
                        placeholder="Search papers, authors, topics..."
                        className="w-full bg-gray-100 border border-gray-200 focus:border-blue-300 pl-12 py-3 rounded-3xl text-sm focus:outline-none transition"
                    />
                </div> */}
            </div>

            {/* Right: New Project + Avatar */}
            <div className="flex items-center gap-4">
                {/* New Project Button */}
                <Link href="/projects/new">
                    <button 
                        onClick={handleCreateProject}
                        disabled={isCreatingProject}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-3xl font-medium flex items-center gap-2 transition-all active:scale-95"
                    >
                        {isCreatingProject ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                Creating...
                            </>
                        ) : (
                            <>
                                <Plus size={18} />
                                New Project
                            </>
                        )}
                        
                    </button>
                </Link>

                {/* User Avatar */}
                <div className="relative" ref={dropdownRef}>
                    <div
                        className="w-9 h-9 bg-orange-100 rounded-full flex items-center justify-center text-2xl cursor-pointer hover:ring-2 hover:ring-orange-200 transition"
                        onClick={() => setDropdownOpen((prev) => !prev)}
                    >
                        <User size={20} />
                    </div>

                    {/* Dropdown Menu */}
                    {dropdownOpen && (
                        <div className ="absolute right-0 mt-2 w-56 bg-white rounded-3xl shadow-xl border border-gray-100 py-2 z-50">
                            <div className="px-4 py-3 border-b border-gray-100">
                                <div className="font-medium">
                                    {user?.user_metadata?.full_name}
                                </div>
                                <div className="text-xs text-gray-500">
                                    {user?.email}
                                </div>
                            </div>

                            <button className="w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-50 text-left text-sm">
                                <Settings size={18} />
                                Settings
                            </button>

                            <div className="h-px bg-gray-100 mx-4 my-1" />

                            <button 
                                onClick={handleLogout}
                                className="w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-50 text-left text-sm text-red-600"
                            >
                                <LogOut size={18} />
                                Logout
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    )

}


