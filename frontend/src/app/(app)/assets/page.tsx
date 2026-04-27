import Link from "next/link";
import { AssetList } from "@/components/features/assets/asset-list";
import { CashAccountList } from "@/components/features/cash/cash-account-list";
import { BulkImportButton } from "@/components/features/transactions/bulk-import-button";
import { Plus } from "lucide-react";

export const metadata = { title: "보유 자산 — AssetLog" };

export default function AssetsPage() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">보유 자산</h1>
        <div className="flex items-center gap-2">
          <BulkImportButton />
          <Link
            href="/assets/new"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
            aria-label="새 자산 추가"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            자산 추가
          </Link>
        </div>
      </div>

      {/* 현금 섹션 — 보유 자산 위 */}
      <section className="mb-8" aria-label="현금 보유">
        <CashAccountList />
      </section>

      <AssetList />
    </div>
  );
}
