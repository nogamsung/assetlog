export default function DashboardLoading() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 h-8 w-32 rounded bg-muted animate-pulse" />
      <div className="space-y-6" role="status" aria-label="대시보드 로딩 중">
        {/* 요약 카드 3개 스켈레톤 */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-28 rounded-xl border bg-muted/40 animate-pulse"
            />
          ))}
        </div>
        {/* 도넛 차트 스켈레톤 */}
        <div className="h-64 rounded-xl border bg-muted/40 animate-pulse" />
        {/* 테이블 스켈레톤 */}
        <div className="rounded-xl border bg-muted/40 animate-pulse">
          <div className="h-12 border-b bg-muted/60 animate-pulse" />
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 border-b last:border-0 bg-muted/40 animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}
