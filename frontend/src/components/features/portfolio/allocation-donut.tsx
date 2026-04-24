"use client";

import { formatPercent } from "@/lib/format";
import type { AllocationEntry } from "@/types/portfolio";

const ASSET_TYPE_LABELS: Record<string, string> = {
  crypto: "암호화폐",
  kr_stock: "국내주식",
  us_stock: "미국주식",
};

const COLORS = ["#3b82f6", "#f97316", "#22c55e", "#a855f7", "#ec4899"];

interface AllocationDonutProps {
  allocation: AllocationEntry[];
}

interface DonutSlice {
  label: string;
  pct: number;
  color: string;
  startAngle: number;
  endAngle: number;
}

function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angleDeg: number,
): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function describeArc(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startAngle: number,
  endAngle: number,
): string {
  const [sx, sy] = polarToCartesian(cx, cy, outerR, startAngle);
  const [ex, ey] = polarToCartesian(cx, cy, outerR, endAngle);
  const [isx, isy] = polarToCartesian(cx, cy, innerR, endAngle);
  const [iex, iey] = polarToCartesian(cx, cy, innerR, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;

  return [
    `M ${sx} ${sy}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${ex} ${ey}`,
    `L ${isx} ${isy}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${iex} ${iey}`,
    "Z",
  ].join(" ");
}

export function AllocationDonut({ allocation }: AllocationDonutProps) {
  if (allocation.length === 0) {
    return (
      <div
        className="flex h-48 items-center justify-center rounded-xl border bg-card"
        aria-label="자산 클래스별 비중 도넛 차트"
      >
        <p className="text-sm text-muted-foreground">데이터 없음</p>
      </div>
    );
  }

  const cx = 100;
  const cy = 100;
  const outerR = 80;
  const innerR = 50;

  const slices: DonutSlice[] = allocation.reduce<DonutSlice[]>((acc, entry, i) => {
    const prev = acc[acc.length - 1];
    const startAngle = prev ? prev.endAngle : 0;
    const endAngle = startAngle + entry.pct * 3.6;
    return [
      ...acc,
      {
        label: ASSET_TYPE_LABELS[entry.assetType] ?? entry.assetType,
        pct: entry.pct,
        color: COLORS[i % COLORS.length],
        startAngle,
        endAngle,
      },
    ];
  }, []);

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="mb-4 text-sm font-medium text-muted-foreground">
        자산 클래스 비중
      </h3>
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <svg
          viewBox="0 0 200 200"
          width={200}
          height={200}
          aria-label="자산 클래스별 비중 도넛 차트"
          role="img"
        >
          <title>자산 클래스별 비중 도넛 차트</title>
          {slices.map((slice) => (
            <path
              key={slice.label}
              d={describeArc(cx, cy, outerR, innerR, slice.startAngle, slice.endAngle)}
              fill={slice.color}
            />
          ))}
        </svg>

        {/* 스크린리더용 텍스트 대안 + 범례 */}
        <ul className="space-y-2 text-sm" aria-label="자산 클래스 비중 목록">
          {slices.map((slice) => (
            <li key={slice.label} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: slice.color }}
                aria-hidden="true"
              />
              <span>
                {slice.label}: <span className="font-medium">{formatPercent(slice.pct)}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
