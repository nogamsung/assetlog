export default function SettingsLoading() {
  return (
    <div
      className="container mx-auto max-w-2xl px-4 py-8 space-y-6"
      role="status"
      aria-label="설정 로딩 중"
    >
      <div className="h-8 w-16 rounded bg-muted animate-pulse" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-xl border bg-muted/40 animate-pulse h-36" />
      ))}
    </div>
  );
}
