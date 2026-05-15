"use client";

import { useState } from "react";
import { Calendar, List } from "lucide-react";
import { cn } from "@/lib/utils";
import { HistoryView } from "./history-view";
import { HistoryCalendar } from "./history-calendar";

type Mode = "list" | "calendar";

const MODES: { value: Mode; label: string; Icon: React.ElementType }[] = [
  { value: "list", label: "목록", Icon: List },
  { value: "calendar", label: "캘린더", Icon: Calendar },
];

export function HistoryTabs() {
  const [mode, setMode] = useState<Mode>("list");

  return (
    <div className="space-y-4">
      <div
        role="group"
        aria-label="보기 모드"
        className="inline-flex items-center gap-1 rounded-xl border border-toss-border bg-muted/40 p-1"
      >
        {MODES.map(({ value, label, Icon }) => {
          const isActive = mode === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isActive}
              aria-label={`${label} 보기`}
              onClick={() => setMode(value)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-toss-blue/40 focus-visible:ring-offset-1",
                isActive
                  ? "bg-toss-card text-toss-textStrong shadow-sm ring-1 ring-toss-border"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>

      {mode === "list" ? <HistoryView /> : <HistoryCalendar />}
    </div>
  );
}
