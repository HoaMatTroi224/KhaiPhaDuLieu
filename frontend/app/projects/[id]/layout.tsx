'use client';
import ChatBox from '@/components/ChatBox';
import BottomTool from '@/components/BottomTool';

export default function ProjectDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <main className="flex flex-1 overflow-hidden">
        {/* Page.tsx sẽ render vào đây */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          {children}
        </div>
      </main>

      {/* Bottom Toolbar */}
      <BottomTool />
    </div>
  );
}


// 'use client';

// import ProjectHeader from '@/components/ProjectHeader';
// import DocumentList from '@/components/DocumentList';
// import DocumentViewer from '@/components/DocumentViewer';
// import ChatBox from '@/components/ChatBox';
// import BottomTool from '@/components/BottomTool';

// export default function ProjectDetailLayout({
//   children,
// }: {
//     children: React.ReactNode
// }) {
//     return (
//         <div className="flex h-screen flex-col bg-gray-50 overflow-hidden">
        
//             {/* Project Topbar */}
//                 <ProjectHeader title="Neural Synthesis in Modern AI Architecture" />

//             <main className="flex flex-1 overflow-hidden">
                
//                 {/* Left Sidebar - Documents */}
//                 <aside className="w-72 border-r border-gray-200 bg-white overflow-y-auto">
//                 <DocumentList />
//                 </aside>

//                 {/* Main Content - Document Viewer */}
//                 <div className="flex-1 flex flex-col overflow-hidden bg-white">
//                     <div className="flex-1 overflow-y-auto p-8">
//                         {children}
//                     </div>
//                 </div>

//                 {/* Right Sidebar - ChatBox */}
//                 <aside className="w-96 border-l border-gray-200 bg-white overflow-y-auto hidden xl:block">
//                 <ChatBox />
//                 </aside>
//             </main>

//             {/* Bottom Toolbar */}
//             <BottomTool />
//         </div>
//     );
// }