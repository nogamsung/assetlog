export default function AssetsLoading() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="h-8 w-32 rounded bg-muted animate-pulse" />
        <div className="h-9 w-28 rounded-md bg-muted animate-pulse" />
      </div>
      <div className="space-y-3" aria-label="보유 자산 로딩 중" role="status">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg border bg-muted/40 animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}
