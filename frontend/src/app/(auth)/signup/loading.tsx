export default function SignupLoading() {
  return (
    <div className="flex items-center justify-center py-12">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
        role="status"
        aria-label="회원가입 페이지 로딩 중"
      />
    </div>
  );
}
