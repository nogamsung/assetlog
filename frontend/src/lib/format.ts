import type { AssetType } from "@/types/asset";

// ── Internal category sets ─────────────────────────────────────────────────────
const INTEGER_CURRENCIES = new Set(["KRW", "JPY"]); // ADDED
const STABLE_LIKE = new Set(["USDT", "USDC", "DAI", "BUSD"]); // ADDED

// ── Options ────────────────────────────────────────────────────────────────────

export interface FormatCurrencyOptions { // ADDED
  /** Use ko-KR compact notation (1.2억). Default false. */
  compact?: boolean;
  /** Remove trailing zeros. Default true. */
  trimTrailingZeros?: boolean;
  /** Fallback string returned when amount is NaN. Default '—'. */ // ADDED
  fallback?: string; // ADDED
}

/**
 * Decimal string을 통화 포맷으로 변환.
 * 백엔드에서 string으로 오는 Decimal 값을 표시 직전에만 Number로 변환.
 * 금액 범위(일반 자산 가격)에서는 Number 정밀도 손실이 허용 가능.
 *
 * USDT / USDC 등 Intl.NumberFormat 미지원 통화는 try/catch 후
 * fallback: "${formattedNumber} ${code}" 형식으로 반환.
 * 기존 함수 시그니처 변경 없음 — options 는 세 번째 선택 인자.
 */
export function formatCurrency(
  amount: string,
  currency: string,
  options?: FormatCurrencyOptions, // ADDED
): string {
  const numericValue = Number(amount);
  if (Number.isNaN(numericValue)) return options?.fallback ?? "—"; // ADDED
  const compact = options?.compact ?? false; // ADDED
  // trimTrailingZeros default true — KRW is integer so it's N/A; for USD/STABLE it matters
  const trim = options?.trimTrailingZeros ?? true; // ADDED

  // Determine max fraction digits by currency category — ADDED
  let maxFraction: number;
  if (INTEGER_CURRENCIES.has(currency)) {
    maxFraction = 0;
  } else if (STABLE_LIKE.has(currency)) {
    maxFraction = 4;
  } else {
    maxFraction = 2;
  }

  // For integer currencies, minFraction is always 0; for others apply trim rule
  const minFraction = trim ? 0 : maxFraction; // ADDED

  try {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency,
      notation: compact ? "compact" : "standard", // ADDED
      minimumFractionDigits: minFraction, // MODIFIED
      maximumFractionDigits: compact ? 1 : maxFraction, // MODIFIED
    }).format(numericValue);
  } catch {
    // USDT, USDC 등 Intl 미지원 통화 코드 fallback
    const formatted = new Intl.NumberFormat("ko-KR", {
      minimumFractionDigits: minFraction, // MODIFIED
      maximumFractionDigits: compact ? 1 : maxFraction, // MODIFIED
    }).format(numericValue);
    return `${formatted} ${currency}`;
  }
}

/**
 * 모바일 카드용 컴팩트 통화 표기 (ko-KR notation:"compact").
 * 예: 120_000_000 KRW → "₩1.2억"
 * ADDED
 */
export function formatCompactCurrency(amount: string | number, currency: string): string {
  return formatCurrency(String(amount), currency, { compact: true });
}

/**
 * 퍼센트 포맷. 트레일링 zero 제거, 부호 옵션 추가.
 * MODIFIED
 */
export interface FormatPercentOptions { // ADDED
  /** 양수에 '+' 부호를 붙인다. Default false. */
  withSign?: boolean;
  /** Fallback string returned when pct is NaN. Default '—'. */ // ADDED
  fallback?: string; // ADDED
}

export function formatPercent(pct: number | string, digits = 2, opts?: FormatPercentOptions): string { // MODIFIED
  const n = typeof pct === "string" ? Number(pct) : pct;
  if (Number.isNaN(n)) return opts?.fallback ?? "—"; // ADDED
  // Trailing zero trim: toFixed → Number → toString removes them
  const trimmed = String(Number(n.toFixed(digits))); // MODIFIED
  const hasDecimal = trimmed.includes(".");
  const formatted = hasDecimal ? trimmed : trimmed; // already trimmed by Number()
  const sign = opts?.withSign && n > 0 ? "+" : ""; // ADDED
  return `${sign}${formatted}%`;
}

/**
 * PnL 색상 — 토스 컬러 규칙 (한국 금융 관습: 상승=빨강 / 하락=파랑).
 * Returns Tailwind class string.
 * ADDED
 */
export function pnlColor(value: string | number): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (n > 0) return "text-toss-up";
  if (n < 0) return "text-toss-down";
  return "text-toss-textWeak";
}

/**
 * 부호 자동 부착 통화 표기.
 * 양수: "+₩1,234" / 음수: "−₩1,234" (U+2212 minus) / 0: "₩0"
 * ADDED
 */
export function formatSignedCurrency(
  amount: string | number,
  currency: string,
  options?: Omit<FormatCurrencyOptions, "compact">,
): string {
  const n = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(n)) return options?.fallback ?? "—"; // ADDED
  const formatted = formatCurrency(String(Math.abs(n)), currency, options);
  if (n > 0) return `+${formatted}`;
  if (n < 0) return `−${formatted}`; // U+2212 minus sign
  return formatted;
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
 * 수량 포맷: crypto → 8자리 소수, 주식 → 4자리 소수.
 * trailing zeros naturally removed by maximumFractionDigits + no minimumFractionDigits.
 */
export function formatQuantity(qty: string, assetType: AssetType, fallback = "—"): string { // MODIFIED
  const n = Number(qty);
  if (Number.isNaN(n)) return fallback; // ADDED
  const digits = assetType === "crypto" ? 8 : 4;
  return n.toLocaleString("ko-KR", { // MODIFIED
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}
