"use client";

import { cn } from "@/lib/utils";

interface CurrencySwitcherProps {
  value: string | null;
  onChange: (currency: string | null) => void;
  availableCurrencies: string[];
}

export function CurrencySwitcher({
  value,
  onChange,
  availableCurrencies,
}: CurrencySwitcherProps) {
  const options: Array<{ label: string; value: string | null }> = [
    { label: "환산 안 함", value: null },
    ...availableCurrencies.map((c) => ({ label: `${c} 환산`, value: c })),
  ];

  return (
    <div
      role="group"
      aria-label="통화 환산 선택"
      className="inline-flex items-center gap-1 rounded-xl border border-toss-border bg-muted/40 p-1"
    >
      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <button
            key={option.value ?? "__none__"}
            type="button"
            aria-pressed={isActive}
            aria-label={option.label}
            onClick={() => onChange(option.value)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-toss-blue/40 focus-visible:ring-offset-1",
              isActive
                ? "bg-toss-card text-toss-textStrong shadow-sm ring-1 ring-toss-border"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
