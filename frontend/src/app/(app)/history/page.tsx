import { HistoryView } from "@/components/features/history/history-view";

export default function HistoryPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">거래 내역</h1>
      <p className="text-sm text-muted-foreground">
        보유 자산의 매수·매도와 현금 입출금을 자산 종류별로 모아 볼 수 있습니다.
      </p>
      <HistoryView />
    </div>
  );
}
