import { PublicNav } from '@/components/marketing/PublicNav';
import { Footer } from '@/components/marketing/Footer';

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
