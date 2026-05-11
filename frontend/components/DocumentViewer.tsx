'use client';

import { useEffect, useRef } from "react";
import { ChevronDown, CheckCircle2 } from "lucide-react";

export default function DocumentViewer() {
    const contentRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Add highlight event listener to the content area
        const handleApplyHighlight = (e: Event) => {
            const customEvent = e as CustomEvent<string>;
            const colorClass = customEvent.detail;
            const selection = window.getSelection();

            // Ensure there's a valid selection
            if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
                return;
            }

            // Check if the selection is within the content area
            const range = selection.getRangeAt(0);
            if (contentRef.current && contentRef.current.contains(range.commonAncestorContainer)) {
                try {
                    // Create a new span element to wrap the selected text
                    const span = document.createElement('span');
                    span.className = `${colorClass} rounded-sm px-0.5 transition-colors cursor-pointer highlight-mark`;

                    // Wrap the selected text with the span
                    range.surroundContents(span);

                    // Clear the selection after applying the highlight
                    selection.removeAllRanges();
                } catch (error) {
                    // Handle any errors that may occur during the highlight process
                    console.error('Error applying highlight:', error);
                }
            }

            if (contentRef.current) {
                // Handle highlight logic here
            }
        };

        document.addEventListener('apply-highlight', handleApplyHighlight);


        // Add clear highlight event listener
        const handleClearHighlight = () => {
            if (!contentRef.current) return;
            const highlights = contentRef.current.querySelectorAll('.highlight-mark');

            highlights.forEach((mark) => {
                const parent = mark.parentNode;
                while (mark.firstChild) {
                    parent?.insertBefore(mark.firstChild, mark);
                }
                parent?.removeChild(mark);
            });
        };

        // Listen for the custom 'clear-highlight' event
        document.addEventListener('apply-highlight', handleApplyHighlight);
        document.addEventListener('clear-highlight', handleClearHighlight);

        // Cleanup event listeners on unmount
        return () => {
            document.removeEventListener('apply-highlight', handleApplyHighlight);
            document.removeEventListener('clear-highlight', handleClearHighlight);
        };
    }, []);

    return (
        <div className="max-w-3xl">
            {/* Source Information */}
            {/* <div className="flex items-center justify-between mb-6">
                <button className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
                    <ChevronDown size={18} />
                    VIEW ORIGINAL TEXT SOURCE
                </button>
                <div className="text-xs text-gray-400">3,420 Words &bull; 12 Pages</div>
            </div> */}

            {/* Paper Content */}
            <div 
                ref={contentRef}
                className="bg-white rounded-[32px] p-12 shadow-sm border border-gray-100"
            >
                {/* Title */}
                <h1 className="text-4xl font-bold text-gray-900 leading-tight mb-8">
                    Synthesis of Multi-Modal Neural Pathways
                </h1>

                {/* Badges */}
                {/* <div className="flex gap-2 mb-8">
                    <span className="px-4 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">VERIFIED INSIGHT</span>
                    <span className="px-4 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">PEER REVIEWED</span>
                </div> */}

                {/* Executive Summary */}
                <div className="mb-10">
                    <h2 className="text-blue-600 font-semibold mb-3">Executive Summary</h2>
                    <p className="text-gray-700 leading-relaxed">
                        The shift toward unified multi-modal architectures marks a significant evolution in artificial intelligence. This document synthesizes the core breakthroughs in bridging visual and textual semantic layers, focusing on the "Stitch" methodology which allows for seamless data integration across disparate modalities.
                    </p>
                </div>

                {/* Key Findings */}
                {/* <div>
                    <h2 className="font-semibold text-lg mb-4">Key Findings</h2>

                    <ul className="space-y-6">
                        <li className="flex items-start gap-4">
                            <div className="mt-1 text-blue-100 bg-blue-50 rounded-full shrink-0">
                                <CheckCircle2 size={18} className="text-blue-600" />
                            </div>
                            <p className="text-gray-700 text-lg leading-relaxed">
                                <strong className="text-gray-900">Cross-Modal Efficiency:</strong> The research indicates a 40% reduction in training latency when utilizing the proposed latent alignment strategy compared to traditional early-fusion models.
                            </p>
                        </li>
                        <li className="flex items-start gap-4">
                            <div className="mt-1 text-blue-100 bg-blue-50 rounded-full shrink-0">
                                <CheckCircle2 size={18} className="text-blue-600" />
                            </div>
                            <p className="text-gray-700 text-lg leading-relaxed">
                                <strong className="text-gray-900">Semantic Cohesion:</strong> By treating visual tokens as linguistic counterparts, models achieve higher zero-shot reasoning capabilities in complex spatial reasoning tasks.
                            </p>
                        </li>
                    </ul>
                </div> */}
            </div>
        </div>
    );
}