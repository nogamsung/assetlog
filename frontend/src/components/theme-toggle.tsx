"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { useThemeStore } from "@/stores/theme";
import type { Theme } from "@/stores/theme";

interface ThemeOption {
  value: Theme;
  label: string;
  Icon: React.ElementType;
}

const THEME_OPTIONS: ThemeOption[] = [
  { value: "light", label: "라이트", Icon: Sun },
  { value: "dark", label: "다크", Icon: Moon },
  { value: "system", label: "시스템", Icon: Monitor },
];

export function ThemeToggle() {
  const { theme, setTheme } = useThemeStore();

  return (
    <div
      role="group"
      aria-label="테마 선택"
      className="inline-flex items-center gap-1 rounded-xl border border-toss-border bg-muted/40 p-1"
    >
      {THEME_OPTIONS.map(({ value, label, Icon }) => {
        const isPressed = theme === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-label={`${label} 테마`}
            aria-pressed={isPressed}
            className={`
              inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium
              transition-[background-color,color,box-shadow,transform] duration-150
              active:scale-[0.96]
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-toss-blue/40 focus-visible:ring-offset-1
              ${
                isPressed
                  ? "bg-toss-card text-toss-textStrong shadow-sm ring-1 ring-toss-border"
                  : "text-muted-foreground hover:text-foreground"
              }
            `}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}
