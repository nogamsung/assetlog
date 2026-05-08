"use client";

import type { FxWarning } from "@/types/portfolio";

interface FxWarningInfoProps {
  warning: FxWarning | undefined;
}

const TOOLTIP_BY_REASON: Record<
  Exclude<FxWarning, null | "same_currency">,
  string
> = {
  missing_historical_rate: "거래일 환율 기록이 누적 중입니다 — 가격/환차 분리는 다음 환율 갱신 후 활성화됩니다.",
  missing_current_rate: "현재 환율 데이터가 없습니다 — 가격/환차 분리를 표시할 수 없습니다.",
};

export function FxWarningInfo({ warning }: FxWarningInfoProps) {
  if (!warning || warning === "same_currency") return null;
  const tooltip = TOOLTIP_BY_REASON[warning];
  return (
    <span
      className="ml-1 inline-flex items-center text-toss-textWeak"
      title={tooltip}
      aria-label="환율 데이터 누적 중"
      role="img"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 16 16"
        width="12"
        height="12"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <text
          x="8"
          y="11"
          textAnchor="middle"
          fontSize="10"
          fontWeight="600"
          fill="currentColor"
        >
          i
        </text>
      </svg>
    </span>
  );
}
