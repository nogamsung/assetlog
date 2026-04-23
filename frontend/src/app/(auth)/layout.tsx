import type { Metadata } from "next";
import { AuthGuard } from "@/components/features/auth/auth-guard";

export const metadata: Metadata = {
  title: "AssetLog",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </AuthGuard>
  );
}
