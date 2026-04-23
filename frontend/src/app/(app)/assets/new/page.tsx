import Link from "next/link";
import { AssetAddFlow } from "@/components/features/assets/asset-add-flow";
import { ArrowLeft } from "lucide-react";

export const metadata = { title: "자산 추가 — AssetLog" };

export default function AssetsNewPage() {
  return (
    <div className="container mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6">
        <Link
          href="/assets"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          aria-label="보유 자산 목록으로 돌아가기"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          보유 자산 목록으로
        </Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">자산 추가</h1>
      <AssetAddFlow />
    </div>
  );
}
