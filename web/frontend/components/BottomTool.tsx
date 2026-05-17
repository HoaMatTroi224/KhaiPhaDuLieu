'use client';

import { Eraser, Wifi, WifiOff } from 'lucide-react';

export default function BottomTool() {
    // Hàm phát sự kiện tô màu
    const handleHighlight = (colorClass: string) => {
        const event = new CustomEvent('apply-highlight', { detail: colorClass });
        document.dispatchEvent(event);
    };

    // Hàm phát sự kiện xóa màu
    const handleClearHighlight = () => {
        document.dispatchEvent(new Event('clear-highlight'));
    };

    return (
        <div className="fixed bottom-0 left-64 right-[380px] p-4 pointer-events-none flex justify-center">
            <div className="bg-white/80 backdrop-blur-md rounded-full shadow-sm border border-gray-100 px-6 py-3 flex items-center gap-8 pointer-events-auto">
                
                {/* Highlight Tools */}
                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mr-2">Highlight Tool</span>
                    {/* Nút màu Vàng */}
                    <button 
                        onClick={() => handleHighlight('bg-yellow-200')}
                        className="w-6 h-6 rounded-full bg-yellow-200 hover:scale-110 hover:ring-2 hover:ring-yellow-200 hover:ring-offset-2 transition-all"
                    ></button>
                    {/* Nút màu Xanh lá */}
                    <button 
                        onClick={() => handleHighlight('bg-green-200')}
                        className="w-6 h-6 rounded-full bg-green-200 hover:scale-110 hover:ring-2 hover:ring-green-200 hover:ring-offset-2 transition-all"
                    ></button>
                    {/* Nút màu Xanh dương */}
                    <button 
                        onClick={() => handleHighlight('bg-blue-200')}
                        className="w-6 h-6 rounded-full bg-blue-200 hover:scale-110 hover:ring-2 hover:ring-blue-200 hover:ring-offset-2 transition-all"
                    ></button>
                    {/* Nút màu Hồng */}
                    <button 
                        onClick={() => handleHighlight('bg-pink-200')}
                        className="w-6 h-6 rounded-full bg-pink-200 hover:scale-110 hover:ring-2 hover:ring-pink-200 hover:ring-offset-2 transition-all"
                    ></button>

                    <div className="w-[1px] h-6 bg-gray-200 mx-2"></div>
                    
                    {/* Nút Clear */}
                    <button 
                        onClick={handleClearHighlight}
                        className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-blue-500 transition-colors"
                    >
                        <Eraser size={14} /> Clear
                    </button>
                </div>

                {/* <div className="w-[1px] h-6 bg-gray-200"></div> */}

                {/* Wifi Status */}
                {/* <div className="flex items-center gap-2 text-xs font-medium text-gray-400 ml-8">
                    <Wifi size={14} className="text-green-400" /> Online Cache
                </div> */}
            </div>
        </div>
    );
}