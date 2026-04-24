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
      className="inline-flex items-center rounded-md border border-input bg-background p-0.5 shadow-sm"
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
              "rounded px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
