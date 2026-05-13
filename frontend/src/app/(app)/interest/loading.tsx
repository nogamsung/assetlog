export default function InterestLoading() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 h-8 w-32 rounded bg-muted animate-pulse" />
      <div className="space-y-4" role="status" aria-label="이자 내역 로딩 중">
        <div className="h-12 w-48 rounded-md bg-muted/40 animate-pulse" />
        <div className="h-64 rounded-xl border bg-muted/40 animate-pulse" />
      </div>
    </div>
  );
}
