export default function AssetsNewLoading() {
  return (
    <div className="container mx-auto max-w-2xl px-4 py-8">
      <div className="h-5 w-40 rounded bg-muted animate-pulse mb-6" />
      <div className="h-8 w-32 rounded bg-muted animate-pulse mb-6" />
      <div className="space-y-4">
        <div className="h-10 rounded-md bg-muted animate-pulse" />
        <div className="h-10 rounded-md bg-muted animate-pulse" />
      </div>
    </div>
  );
}
