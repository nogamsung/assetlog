import { Badge } from "@/components/ui/badge";

export function PendingBadge() {
  return (
    <Badge
      variant="secondary"
      aria-label="현재가 대기 중"
      className="bg-yellow-100 text-yellow-800 border-transparent hover:bg-yellow-100/80"
    >
      가격 대기중
    </Badge>
  );
}
