import { Badge } from "@/components/ui/badge";

export function StaleBadge() {
  return (
    <Badge
      variant="outline"
      aria-label="가격 정보 지연됨"
      className="border-orange-300 text-orange-700"
    >
      지연
    </Badge>
  );
}
