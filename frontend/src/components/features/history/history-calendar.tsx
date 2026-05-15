"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { useAllTransactions } from "@/hooks/use-transactions";
import { useAllCashTransactions } from "@/hooks/use-cash-accounts";
import { formatCurrency, formatQuantity, pnlColor } from "@/lib/format";
import type { TransactionWithSymbolResponse } from "@/types/transaction";
import type { CashAccountTransaction } from "@/types/cash-account";

const SOURCE_LABELS: Record<string, string> = {
  toss_investment: "토스증권",
  shinhan_investment: "신한투자증권",
  k_bank: "케이뱅크",
  upbit: "업비트",
  bithumb: "빗썸",
  binance: "바이낸스",
  kis: "한국투자증권",
  manual: "수동 입력",
};

function sourceLabel(s: string | null | undefined): string {
  if (!s) return "수동 입력";
  return SOURCE_LABELS[s] ?? s;
}

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

/** Return YYYY-MM-DD in KST regardless of the browser's TZ. */
function kstDateKey(iso: string): string {
  const d = new Date(iso);
  // Shift to KST (UTC+9) so day boundaries line up with the user's brokerage tz.
  const kst = new Date(d.getTime() + 9 * 60 * 60 * 1000);
  return kst.toISOString().slice(0, 10);
}

function ymdKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

interface DayBuckets {
  trades: TransactionWithSymbolResponse[];
  cash: CashAccountTransaction[];
}

export function HistoryCalendar() {
  const tradesQ = useAllTransactions();
  const cashQ = useAllCashTransactions();

  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed
  const [openDay, setOpenDay] = useState<string | null>(null);

  // Group every transaction by its KST-local date key.
  const byDate = useMemo(() => {
    const m = new Map<string, DayBuckets>();
    for (const t of tradesQ.data ?? []) {
      const k = kstDateKey(t.tradedAt);
      const b = m.get(k) ?? { trades: [], cash: [] };
      b.trades.push(t);
      m.set(k, b);
    }
    for (const c of cashQ.data ?? []) {
      if (c.kind !== "deposit" && c.kind !== "withdraw") continue;
      const k = kstDateKey(c.tradedAt);
      const b = m.get(k) ?? { trades: [], cash: [] };
      b.cash.push(c);
      m.set(k, b);
    }
    return m;
  }, [tradesQ.data, cashQ.data]);

  // Build the 6×7 grid for the visible month. First cell is the Sunday on or
  // before the 1st of the month; last cell carries the grid to 42 entries so
  // the layout doesn't reflow as the user pages.
  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1);
    const startDow = first.getDay(); // 0 = Sun
    const grid: { date: Date; inMonth: boolean }[] = [];
    const start = new Date(viewYear, viewMonth, 1 - startDow);
    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      grid.push({ date: d, inMonth: d.getMonth() === viewMonth });
    }
    return grid;
  }, [viewYear, viewMonth]);

  function goPrev() {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  }
  function goNext() {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  }
  function goToday() {
    const t = new Date();
    setViewYear(t.getFullYear());
    setViewMonth(t.getMonth());
  }

  const isLoading = tradesQ.isLoading || cashQ.isLoading;
  const monthLabel = `${viewYear}년 ${viewMonth + 1}월`;

  const todayKey = ymdKey(today);
  const openBuckets = openDay ? byDate.get(openDay) : undefined;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={goPrev}
            aria-label="이전 달"
            className="rounded-lg p-2 hover:bg-muted transition-colors"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          <h2 className="px-2 text-sm font-bold text-toss-textStrong tabular-nums">
            {monthLabel}
          </h2>
          <button
            type="button"
            onClick={goNext}
            aria-label="다음 달"
            className="rounded-lg p-2 hover:bg-muted transition-colors"
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <button
          type="button"
          onClick={goToday}
          aria-label="오늘로 이동"
          className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground hover:bg-muted/70 transition-colors"
        >
          오늘
        </button>
      </div>

      <div className="rounded-2xl border border-toss-border bg-toss-card p-3">
        {isLoading ? (
          <div
            role="status"
            aria-label="캘린더 로딩 중"
            className="h-64 rounded bg-muted/40 animate-pulse"
          />
        ) : (
          <>
            <div className="grid grid-cols-7 gap-px text-center text-xs text-muted-foreground">
              {WEEKDAYS.map((w, i) => (
                <div
                  key={w}
                  className={`py-1.5 ${
                    i === 0 ? "text-toss-down" : i === 6 ? "text-toss-blue" : ""
                  }`}
                >
                  {w}
                </div>
              ))}
            </div>
            <div className="mt-1 grid grid-cols-7 gap-1">
              {cells.map(({ date, inMonth }) => {
                const key = ymdKey(date);
                const buckets = byDate.get(key);
                const tradeCount = buckets?.trades.length ?? 0;
                const cashCount = buckets?.cash.length ?? 0;
                const hasAny = tradeCount + cashCount > 0;
                const isToday = key === todayKey;
                const dow = date.getDay();

                let buyCount = 0;
                let sellCount = 0;
                for (const t of buckets?.trades ?? []) {
                  if (t.type === "buy") buyCount++;
                  else sellCount++;
                }
                let depCount = 0;
                let wdrCount = 0;
                for (const c of buckets?.cash ?? []) {
                  if (c.kind === "deposit") depCount++;
                  else wdrCount++;
                }

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => hasAny && setOpenDay(key)}
                    disabled={!hasAny}
                    aria-label={`${key}${hasAny ? ` 거래 ${tradeCount + cashCount}건` : ""}`}
                    className={`group relative flex min-h-[64px] flex-col items-stretch rounded-lg border p-1.5 text-left transition-colors ${
                      inMonth
                        ? hasAny
                          ? "border-toss-border bg-toss-bg hover:border-toss-blue hover:bg-toss-blue/5 cursor-pointer"
                          : "border-toss-border bg-toss-bg"
                        : "border-transparent bg-transparent text-muted-foreground/40"
                    } ${isToday ? "ring-1 ring-toss-blue" : ""}`}
                  >
                    <span
                      className={`text-xs font-medium tabular-nums ${
                        !inMonth
                          ? "text-muted-foreground/40"
                          : dow === 0
                            ? "text-toss-down"
                            : dow === 6
                              ? "text-toss-blue"
                              : "text-toss-textStrong"
                      }`}
                    >
                      {date.getDate()}
                    </span>
                    {hasAny && inMonth && (
                      <div className="mt-auto flex flex-wrap gap-0.5 pt-1">
                        {buyCount > 0 && (
                          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-toss-up" aria-label={`매수 ${buyCount}건`} />
                        )}
                        {sellCount > 0 && (
                          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-toss-down" aria-label={`매도 ${sellCount}건`} />
                        )}
                        {depCount > 0 && (
                          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-toss-blue" aria-label={`입금 ${depCount}건`} />
                        )}
                        {wdrCount > 0 && (
                          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-toss-textWeak" aria-label={`출금 ${wdrCount}건`} />
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            <div className="mt-3 flex flex-wrap gap-3 px-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-toss-up" />
                매수
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-toss-down" />
                매도
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-toss-blue" />
                입금
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-toss-textWeak" />
                출금
              </span>
            </div>
          </>
        )}
      </div>

      <BottomSheet open={openDay !== null} onOpenChange={(v) => !v && setOpenDay(null)}>
        <BottomSheetContent aria-label="해당일 거래 내역">
          <BottomSheetHeader>
            <BottomSheetTitle>{openDay ?? ""}</BottomSheetTitle>
          </BottomSheetHeader>
          {openBuckets ? (
            <div className="space-y-4 pb-4">
              {openBuckets.trades.length > 0 && (
                <section className="space-y-1.5">
                  <p className="text-xs font-semibold text-muted-foreground">
                    매수 · 매도 ({openBuckets.trades.length}건)
                  </p>
                  <ul className="space-y-1.5">
                    {openBuckets.trades.map((t) => {
                      const gross = Number(t.quantity) * Number(t.price);
                      return (
                        <li
                          key={t.id}
                          className="flex items-center justify-between rounded-xl border border-toss-border bg-toss-card px-3 py-2 text-sm"
                        >
                          <div className="min-w-0">
                            <p className="flex items-center gap-2">
                              <span
                                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                                  t.type === "buy"
                                    ? "bg-toss-up/10 text-toss-up"
                                    : "bg-toss-down/10 text-toss-down"
                                }`}
                              >
                                {t.type === "buy" ? "매수" : "매도"}
                              </span>
                              <span className="font-medium truncate">{t.symbol}</span>
                              {t.name && (
                                <span className="text-xs text-muted-foreground truncate">
                                  {t.name}
                                </span>
                              )}
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground tabular-nums">
                              {formatQuantity(t.quantity, t.assetType)} @{" "}
                              {formatCurrency(t.price, t.currency)} · {sourceLabel(t.externalSource)}
                            </p>
                          </div>
                          <span
                            className={`whitespace-nowrap text-sm font-semibold tabular-nums ${pnlColor(
                              t.type === "sell" ? gross : -gross,
                            )}`}
                          >
                            {t.type === "sell" ? "+" : "−"}
                            {formatCurrency(String(gross), t.currency)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}
              {openBuckets.cash.length > 0 && (
                <section className="space-y-1.5">
                  <p className="text-xs font-semibold text-muted-foreground">
                    현금 입출금 ({openBuckets.cash.length}건)
                  </p>
                  <ul className="space-y-1.5">
                    {openBuckets.cash.map((c) => (
                      <li
                        key={c.id}
                        className="flex items-center justify-between rounded-xl border border-toss-border bg-toss-card px-3 py-2 text-sm"
                      >
                        <div>
                          <p className="flex items-center gap-2">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                                c.kind === "deposit"
                                  ? "bg-toss-up/10 text-toss-up"
                                  : "bg-toss-down/10 text-toss-down"
                              }`}
                            >
                              {c.kind === "deposit" ? "입금" : "출금"}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {sourceLabel(c.externalSource)}
                            </span>
                          </p>
                        </div>
                        <span
                          className={`whitespace-nowrap text-sm font-semibold tabular-nums ${pnlColor(
                            c.kind === "deposit" ? Number(c.amount) : -Number(c.amount),
                          )}`}
                        >
                          {c.kind === "deposit" ? "+" : "−"}
                          {formatCurrency(c.amount, c.currency)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          ) : null}
        </BottomSheetContent>
      </BottomSheet>
    </div>
  );
}
