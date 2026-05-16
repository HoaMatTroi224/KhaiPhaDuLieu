'use client';
import { useCallback, useRef, useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import DocumentViewer from '@/components/DocumentViewer';
import DocumentList from '@/components/DocumentList';
import ProjectHeader from '@/components/ProjectHeader';
import { useAuth } from '@/lib/hooks/useAuth';
import ChatBox from '@/components/ChatBox';

const DEFAULT_LEFT_WIDTH = 288;
const DEFAULT_RIGHT_WIDTH = 440;
const MIN_LEFT_WIDTH = 220;
const MAX_LEFT_WIDTH = 420;
const MIN_MAIN_WIDTH = 480;
const MIN_RIGHT_WIDTH = 340;
const MAX_RIGHT_WIDTH = 640;

type Summary = {
  summary_text: string;
};

export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = typeof params.id === 'string' ? params.id : '';
  const initialProjectTitle = searchParams.get('title')?.trim() || 'Untitled Project';
  const { token, loading: authLoading } = useAuth();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocTitle, setSelectedDocTitle] = useState<string>('');
  const [projectTitle, setProjectTitle] = useState<string>(initialProjectTitle);
  const [currentSummary, setCurrentSummary] = useState<Summary | null>(null);
  const [leftWidth, setLeftWidth] = useState(DEFAULT_LEFT_WIDTH);
  const [rightWidth, setRightWidth] = useState(DEFAULT_RIGHT_WIDTH);
  const [threadId] = useState<string>(crypto.randomUUID());
  const layoutRef = useRef<HTMLDivElement>(null);

  const handleSelectedDoc = useCallback((doc: { id: string; title?: string | null; file_name?: string | null }) => {
    setSelectedDocId(doc.id);
    const label = doc.title?.trim() || doc.file_name?.trim() || '';
    setSelectedDocTitle(label);
    setCurrentSummary(null);
  }, []);

  const handleDownloadSummary = useCallback(() => {
    if (!currentSummary) return;

    const summaryTitle = selectedDocTitle.trim() || 'Document Summary';
    const content = `${summaryTitle}\n\n${currentSummary.summary_text}\n`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const safeFileName = summaryTitle
      .replace(/[\\/:*?"<>|]+/g, '')
      .replace(/\s+/g, '_')
      .slice(0, 120) || 'summary';

    link.href = url;
    link.download = `${safeFileName}_summary.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, [currentSummary, selectedDocTitle]);

  useEffect(() => {
    if (!projectId || !token || authLoading) return;
    const fetchProject = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects/${projectId}`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        if (!res.ok) throw new Error('Failed to fetch project');
        const data = await res.json();
        if (data.is_draft) {
          router.replace(`/projects/new?project_id=${projectId}`);
          return;
        }
        setProjectTitle(data.name)
      } catch (err) {
        console.error('Error occured while trying to fetch project:', err);
        setProjectTitle('Untitled Project')
      }
    };

    fetchProject();
  }, [projectId, token, authLoading, router])

  const startResize = useCallback((
    target: 'left' | 'right',
    event: React.PointerEvent<HTMLDivElement>
  ) => {
    event.preventDefault();

    const layoutWidth = layoutRef.current?.getBoundingClientRect().width ?? window.innerWidth;
    const chatIsVisible = window.matchMedia('(min-width: 1280px)').matches;
    const startX = event.clientX;
    const startLeftWidth = leftWidth;
    const startRightWidth = rightWidth;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const clamp = (value: number, min: number, max: number) => {
      return Math.min(Math.max(value, min), max);
    };

    const handlePointerMove = (moveEvent: PointerEvent) => {
      const deltaX = moveEvent.clientX - startX;

      if (target === 'left') {
        const rightReservedWidth = chatIsVisible ? startRightWidth : 0;
        const maxAllowedLeftWidth = Math.min(
          MAX_LEFT_WIDTH,
          layoutWidth - rightReservedWidth - MIN_MAIN_WIDTH
        );
        setLeftWidth(clamp(
          startLeftWidth + deltaX,
          MIN_LEFT_WIDTH,
          Math.max(MIN_LEFT_WIDTH, maxAllowedLeftWidth)
        ));
        return;
      }

      const maxAllowedRightWidth = Math.min(
        MAX_RIGHT_WIDTH,
        layoutWidth - startLeftWidth - MIN_MAIN_WIDTH
      );
      setRightWidth(clamp(
        startRightWidth - deltaX,
        MIN_RIGHT_WIDTH,
        Math.max(MIN_RIGHT_WIDTH, maxAllowedRightWidth)
      ));
    };

    const handlePointerUp = () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
  }, [leftWidth, rightWidth]);

  return (
    <div className="flex flex-col h-full">
      {/* Project Topbar */}
      <ProjectHeader
        title={projectTitle}
        canDownloadSummary={Boolean(currentSummary)}
        onDownloadSummary={handleDownloadSummary}
      />
      
      <div ref={layoutRef} className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Document List */}
        <aside
          className="border-r border-gray-200 bg-white overflow-y-auto shrink-0"
          style={{ flexBasis: leftWidth, width: leftWidth }}
        >
          <DocumentList 
            projectId={projectId} 
            selectedDocId={selectedDocId} 
            onSelectedDoc={handleSelectedDoc}
          />
        </aside>

        <div
          role="separator"
          aria-label="Resize documents column"
          aria-orientation="vertical"
          onPointerDown={(event) => startResize('left', event)}
          onDoubleClick={() => setLeftWidth(DEFAULT_LEFT_WIDTH)}
          className="w-1.5 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-blue-200 active:bg-blue-300"
        />

        {/* Main Viewer - Document Viewer */}
        <main className="flex-1 min-w-0 p-8 overflow-y-auto">
          <DocumentViewer
            selectedDocId={selectedDocId}
            documentTitle={selectedDocTitle}
            onLoadedSummary={setCurrentSummary}
          />
        </main>

        <div
          role="separator"
          aria-label="Resize chat column"
          aria-orientation="vertical"
          onPointerDown={(event) => startResize('right', event)}
          onDoubleClick={() => setRightWidth(DEFAULT_RIGHT_WIDTH)}
          className="hidden xl:block w-1.5 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-blue-200 active:bg-blue-300"
        />

        {/* Right Panel - Chat Box */}
        <aside
          className="shrink-0 border-l border-gray-200 bg-white overflow-y-auto hidden xl:block"
          style={{ flexBasis: rightWidth, width: rightWidth }}
        >
          <ChatBox 
            projectId={projectId}
            threadId={threadId}
          />
        </aside>
      </div>
    </div>
  );
}
