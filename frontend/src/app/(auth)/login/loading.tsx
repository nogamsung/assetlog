export default function LoginLoading() {
  return (
    <div className="flex items-center justify-center py-12">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
        role="status"
        aria-label="로그인 페이지 로딩 중"
      />
    </div>
  );
}
