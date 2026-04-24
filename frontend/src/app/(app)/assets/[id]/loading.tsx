export default function AssetDetailLoading() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 h-8 w-48 rounded bg-muted animate-pulse" />
      <div className="space-y-4">
        <div className="h-32 rounded-xl border bg-muted/40 animate-pulse" />
        <div className="h-48 rounded-xl border bg-muted/40 animate-pulse" />
        <div className="h-64 rounded-xl border bg-muted/40 animate-pulse" />
      </div>
    </div>
  );
}
