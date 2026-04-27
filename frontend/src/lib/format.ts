import type { AssetType } from "@/types/asset";

/**
 * Decimal string을 통화 포맷으로 변환.
 * 백엔드에서 string으로 오는 Decimal 값을 표시 직전에만 Number로 변환.
 * 금액 범위(일반 자산 가격)에서는 Number 정밀도 손실이 허용 가능.
 *
 * USDT / USDC 등 Intl.NumberFormat 미지원 통화는 try/catch 후
 * fallback: "${formattedNumber} ${code}" 형식으로 반환.
 * 기존 함수 시그니처 변경 없음.
 */
export function formatCurrency(amount: string, currency: string): string {
  const numericValue = Number(amount);
  try {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(numericValue);
  } catch {
    // USDT, USDC 등 Intl 미지원 통화 코드 fallback
    const formatted = new Intl.NumberFormat("ko-KR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }).format(numericValue);
    return `${formatted} ${currency}`;
  }
}

/**
 * 퍼센트 포맷 ("13.64%")
 */
export function formatPercent(pct: number, digits = 2): string {
  return `${pct.toFixed(digits)}%`;
}

/**
 * ISO 날짜 문자열을 한국어 상대 시간으로 변환.
 * null → "—"
 */
export function formatRelativeTime(iso: string | null): string {
  if (iso === null) return "—";

  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "방금 전 업데이트";
  if (diffMin < 60) return `${diffMin}분 전 업데이트`;
  if (diffHour < 24) return `${diffHour}시간 전 업데이트`;
  return `${diffDay}일 전 업데이트`;
}

/**
 * 수량 포맷: crypto → 8자리 소수, 주식 → 4자리 소수
 */
export function formatQuantity(qty: string, assetType: AssetType): string {
  const digits = assetType === "crypto" ? 8 : 4;
  return Number(qty).toLocaleString("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}
