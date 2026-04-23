import { Badge } from "@/components/ui/badge";
import type { AssetType } from "@/types/asset";

const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  crypto: "암호화폐",
  kr_stock: "국내주식",
  us_stock: "미국주식",
};

interface AssetTypeBadgeProps {
  assetType: AssetType;
}

export function AssetTypeBadge({ assetType }: AssetTypeBadgeProps) {
  return (
    <Badge variant={assetType} aria-label={`자산 유형: ${ASSET_TYPE_LABELS[assetType]}`}>
      {ASSET_TYPE_LABELS[assetType]}
    </Badge>
  );
}
