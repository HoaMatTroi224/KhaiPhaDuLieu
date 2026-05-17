// app/(main)/layout.tsx
import TopNav from '@/components/TopNav';
import SideBar from '@/components/SideBar';

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <TopNav />
      <div className="flex">
        <SideBar />
        <main className="flex-1 ml-64 mt-[73px] p-6 min-h-screen">
          {children}
        </main>
      </div>
    </>
  );
}