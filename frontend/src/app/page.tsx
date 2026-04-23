import { HomeHeader } from "@/components/features/home-header";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <HomeHeader />
      <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <h2 className="text-2xl font-semibold">환영합니다</h2>
        <p className="text-muted-foreground">
          자산 현황 대시보드는 다음 버전에서 제공됩니다.
        </p>
      </main>
    </div>
  );
}
