import Link from "next/link";
import { HomeHeader } from "@/components/features/home-header";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <HomeHeader />
      <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
        <h2 className="text-2xl font-semibold">환영합니다</h2>
        <p className="text-muted-foreground">
          자산 현황 대시보드는 다음 버전에서 제공됩니다.
        </p>
        <Link
          href="/assets"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
        >
          보유 자산 보기
        </Link>
      </main>
    </div>
  );
}
