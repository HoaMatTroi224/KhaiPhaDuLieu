'use client';

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";

type Summary = {
    summary_text: string;
};

type LoadStatus = 'processing' | 'indexed' | 'failed';

type ViewerState = {
    docId: string | null;
    summary: Summary | null;
    status: LoadStatus;
    retryAttempt: number;
    error: string | null;
};

export default function DocumentViewer({
    selectedDocId,
    documentTitle,
}: {
    selectedDocId: string | null;
    documentTitle?: string;
}) {
    const { token, loading: authLoading } = useAuth();
    const [viewerState, setViewerState] = useState<ViewerState>({
        docId: null,
        summary: null,
        status: 'processing',
        retryAttempt: 0,
        error: null,
    });
    const contentRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleApplyHighlight = (e: Event) => {
            const customEvent = e as CustomEvent<string>;
            const colorClass = customEvent.detail;
            const selection = window.getSelection();

            if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
                return;
            }

            const range = selection.getRangeAt(0);
            if (contentRef.current && contentRef.current.contains(range.commonAncestorContainer)) {
                try {
                    const span = document.createElement('span');
                    span.className = `${colorClass} rounded-sm px-0.5 transition-colors cursor-pointer highlight-mark`;

                    range.surroundContents(span);
                    selection.removeAllRanges();
                } catch (error) {
                    console.error('Error applying highlight:', error);
                }
            }
        };

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

        document.addEventListener('apply-highlight', handleApplyHighlight);
        document.addEventListener('clear-highlight', handleClearHighlight);

        return () => {
            document.removeEventListener('apply-highlight', handleApplyHighlight);
            document.removeEventListener('clear-highlight', handleClearHighlight);
        };
    }, []);

    useEffect(() => {
        if (!selectedDocId || !token || authLoading) return;

        let isMounted = true;
        let retryCount = 0;
        let retryTimer: ReturnType<typeof setTimeout> | null = null;
        const MAX_RETRIES = 72;
        const RETRY_DELAY_MS = 5_000;

        const fetchSummary = async () => {
            try {
                setViewerState({
                    docId: selectedDocId,
                    summary: null,
                    status: "processing",
                    retryAttempt: retryCount,
                    error: null,
                });
                
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries?document_id=${selectedDocId}`, {
                    method: 'GET',
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                if (!res.ok) throw new Error('Failed to fetch summary');

                const data: Summary[] = await res.json();
                if (!isMounted) return;

                if (data.length > 0) {
                    setViewerState({
                        docId: selectedDocId,
                        summary: data[0],
                        status: 'indexed',
                        retryAttempt: retryCount,
                        error: null,
                    });
                    return;
                }

                if (retryCount < MAX_RETRIES) {
                    retryCount++;
                    setViewerState({
                        docId: selectedDocId,
                        summary: null,
                        status: 'processing',
                        retryAttempt: retryCount,
                        error: null,
                    });
                    retryTimer = setTimeout(fetchSummary, RETRY_DELAY_MS);
                    return;
                }

                setViewerState({
                    docId: selectedDocId,
                    summary: null,
                    status: 'failed',
                    retryAttempt: retryCount,
                    error: 'Summary is not available yet. Please try again later.',
                });
            } catch (err: unknown) {
                if (!isMounted) return;

                if (retryCount < MAX_RETRIES) {
                    retryCount++;
                    setViewerState({
                        docId: selectedDocId,
                        summary: null,
                        status: 'processing',
                        retryAttempt: retryCount,
                        error: null,
                    });
                    retryTimer = setTimeout(fetchSummary, RETRY_DELAY_MS);
                    return;
                }

                setViewerState({
                    docId: selectedDocId,
                    summary: null,
                    status: 'failed',
                    retryAttempt: retryCount,
                    error: err instanceof Error
                        ? err.message
                        : 'Error occured while trying to load summaries',
                });
            }
        };

        fetchSummary();

        return () => {
            isMounted = false;
            if (retryTimer) clearTimeout(retryTimer);
        };
    }, [selectedDocId, token, authLoading]);

    const renderContent = () => {
        const isCurrentDocState = viewerState.docId === selectedDocId;
        const isWaitingForCurrentDoc = Boolean(selectedDocId) && !isCurrentDocState;
        const status = isCurrentDocState ? viewerState.status : "uploaded"
        const summary = isCurrentDocState ? viewerState.summary : null;
        const error = isCurrentDocState ? viewerState.error : null;
        const retryAttempt = isCurrentDocState ? viewerState.retryAttempt : 0;

        if (!selectedDocId) {
            return (
                <div className="min-h-[420px] flex items-center justify-center text-center text-gray-400">
                    Select a document to view summary
                </div>
            );
        }

        if (isWaitingForCurrentDoc || authLoading) {
            return (
                <div className="min-h-[420px] flex flex-col items-center justify-center gap-3 text-center text-gray-500">
                    <Loader2 size={22} className="animate-spin text-blue-500" />
                    <p>Preparing summary...</p>
                </div>
            );
        }

        if (status === 'processing') {
            return (
                <div className="min-h-[420px] flex flex-col items-center justify-center gap-3 text-center text-gray-500">
                    <Loader2 size={22} className="animate-spin text-blue-500" />
                    <p>This task may take a few minutes.</p>
                    {/* <p className="text-sm text-gray-400">Loading... ({retryAttempt}/10)</p> */}
                </div>
            );
        }

        if (status === 'failed') {
            return (
                <div className="min-h-[420px] flex flex-col items-center justify-center gap-3 text-center text-gray-500">
                    <p>{error || 'Summarization failed'}</p>
                    <p className="text-sm text-gray-400">Please try again later.</p>
                </div>
            );
        }

        if (status === 'indexed' && summary) {
            return (
                <>
                <h1 className="text-4xl font-bold text-gray-900 leading-tight mb-8">
                    {documentTitle?.trim() || 'Document Summary'}
                </h1>

                <div className="mb-10">
                    <p className="text-gray-700 leading-relaxed">
                    {summary.summary_text}
                    </p>
                </div>
                </>
            );
        }

        return (
            <div className="min-h-[420px] flex flex-col items-center justify-center gap-3 text-center text-gray-500">
                <p>Summary is not available yet.</p>
            </div>
        );
    };

    return (
        <div className="max-w-3xl w-full">
            <div
                ref={contentRef}
                className="bg-white rounded-[32px] p-12 shadow-sm border border-gray-100 min-h-[360px]"
            >
                {renderContent()}
            </div>
        </div>
    );
}
