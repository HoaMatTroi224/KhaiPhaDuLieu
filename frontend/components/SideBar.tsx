'use client';
import Link from 'next/link';
import { ChevronRight, Home, Library } from 'lucide-react';
import { usePathname } from 'next/navigation';

export default function SideBar() {
    const pathname = usePathname();

    const navItems = [
        { label: 'Home', icon: Home, href: '/dashboard', active: pathname === '/dashboard' },
        { label: 'Library', icon: Library, href: '/library', active: pathname === '/library' },
    ];

    return (
        <div className="w-64 bg-white border-r border-gray-100 h-screen flex flex-col pt-6 px-4 fixed left-0 top-[73px] z-40 overflow-y-auto">
            <div className="px-4 mb-8">
                <div className="text-blue-600 font-semibold text-lg tracking-tight">Research Hub</div>
                <div className="text-gray-400 text-sm">Academic Curator</div>
            </div>

            <nav className="px-2 space-y-1 flex-1">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                                item.active
                                    ? 'bg-blue-50 text-blue-600 shadow-sm'
                                    : 'hover:bg-gray-100 text-gray-700'
                            }`}
                        >
                            <Icon size={20} />
                            {item.label}
                            {item.active && <ChevronRight size={16} className="ml-auto" />}
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
}