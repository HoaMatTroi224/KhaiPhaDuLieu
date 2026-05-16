'use client';
import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import DocumentViewer from '@/components/DocumentViewer';
import DocumentList from '@/components/DocumentList';
import ProjectHeader from '@/components/ProjectHeader';
import { useAuth } from '@/lib/hooks/useAuth';
import ChatBox from '@/components/ChatBox';

export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = typeof params.id === 'string' ? params.id : '';
  const { token, loading: authLoading } = useAuth();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocTitle, setSelectedDocTitle] = useState<string>('');
  const [projectTitle, setProjectTitle] = useState<string>('Untitled Project');
  const [threadId] = useState<string>(crypto.randomUUID());
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

  return (
    <div className="flex flex-col h-full">
      {/* Project Topbar */}
      <ProjectHeader title={projectTitle} />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Document List */}
        <aside className="w-72 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
          <DocumentList 
            projectId={projectId} 
            selectedDocId={selectedDocId} 
            onSelectedDoc={(doc) => {
              setSelectedDocId(doc.id);
              const label = (doc.title && doc.title.trim()) || '';
              setSelectedDocTitle(label);
            }} 
          />
        </aside>

        {/* Main Viewer - Document Viewer */}
        <main className="flex-1 p-8 overflow-y-auto">
          <DocumentViewer selectedDocId={selectedDocId} documentTitle={selectedDocTitle} />
        </main>

        {/* Right Panel - Chat Box */}
        <aside className="w-[440px] shrink-0 border-l border-gray-200 bg-white overflow-y-auto hidden xl:block">
          <ChatBox 
            projectId={projectId}
            threadId={threadId}
          />
        </aside>
      </div>
    </div>
  );
}
