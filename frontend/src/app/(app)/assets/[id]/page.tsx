import { AssetDetail } from "@/components/features/assets/asset-detail";

interface AssetDetailPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: AssetDetailPageProps) {
  const { id } = await params;
  return { title: `자산 상세 #${id} — AssetLog` };
}

export default async function AssetDetailPage({ params }: AssetDetailPageProps) {
  const { id } = await params;
  const userAssetId = Number(id);

  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <AssetDetail userAssetId={userAssetId} />
    </div>
  );
}
