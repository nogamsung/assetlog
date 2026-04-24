import { DashboardView } from "@/components/features/portfolio/dashboard-view";

export const metadata = { title: "대시보드 — AssetLog" };

export default function DashboardPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">대시보드</h1>
      <DashboardView />
    </div>
  );
}
