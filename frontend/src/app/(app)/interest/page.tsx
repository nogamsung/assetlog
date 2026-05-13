import { InterestView } from "@/components/features/interest/interest-view";

export const metadata = { title: "이자 내역 — AssetLog" };

export default function InterestPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">이자 내역</h1>
      <InterestView />
    </div>
  );
}
