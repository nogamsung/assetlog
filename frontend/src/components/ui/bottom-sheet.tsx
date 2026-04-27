"use client";

/**
 * BottomSheet — Toss-style mobile bottom sheet / desktop centered dialog.
 *
 * On <sm: slides up from bottom with rounded-t-3xl, handle bar, safe-area pb.
 * On >=sm: centered dialog with rounded-2xl.
 *
 * No external dependency — pure Tailwind + React state.
 * Parallel exports to Dialog: BottomSheet, BottomSheetTrigger,
 * BottomSheetContent, BottomSheetHeader, BottomSheetTitle, BottomSheetFooter.
 */

import * as React from "react";
import { cn } from "@/lib/utils";

/* ── Context ────────────────────────────────────────────────────────────── */

interface BottomSheetContextValue {
  open: boolean;
  setOpen: (v: boolean) => void;
}

const BottomSheetContext = React.createContext<BottomSheetContextValue | null>(null);

function useBottomSheet() {
  const ctx = React.useContext(BottomSheetContext);
  if (!ctx) throw new Error("BottomSheet components must be used inside <BottomSheet>");
  return ctx;
}

/* ── Root ───────────────────────────────────────────────────────────────── */

interface BottomSheetProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

function BottomSheet({ open: controlledOpen, onOpenChange, children }: BottomSheetProps) {
  const [internalOpen, setInternalOpen] = React.useState(false);

  const open = controlledOpen ?? internalOpen;
  const setOpen = React.useCallback(
    (v: boolean) => {
      setInternalOpen(v);
      onOpenChange?.(v);
    },
    [onOpenChange],
  );

  // Close on Escape
  React.useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  // Lock body scroll while open
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <BottomSheetContext.Provider value={{ open, setOpen }}>
      {children}
    </BottomSheetContext.Provider>
  );
}

/* ── Trigger ────────────────────────────────────────────────────────────── */

interface BottomSheetTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Reserved for future use (asChild pattern). Ignored in current implementation. */
  asChild?: boolean;
}

function BottomSheetTrigger({ onClick, children, ...props }: Omit<BottomSheetTriggerProps, 'asChild'>) {
  const { setOpen } = useBottomSheet();
  return (
    <button
      type="button"
      onClick={(e) => {
        setOpen(true);
        onClick?.(e);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

/* ── Content ────────────────────────────────────────────────────────────── */

interface BottomSheetContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function BottomSheetContent({ className, children, ...props }: BottomSheetContentProps) {
  const { open, setOpen } = useBottomSheet();

  if (!open) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end sm:items-center sm:justify-center"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop overlay */}
      <div
        className="absolute inset-0 bg-black/40"
        aria-hidden="true"
        onClick={() => setOpen(false)}
      />

      {/* Sheet / dialog */}
      <div
        className={cn(
          /* Mobile: bottom sheet */
          "relative z-10 w-full max-h-[90vh] overflow-y-auto overscroll-contain",
          "rounded-t-3xl bg-toss-bg px-5 pb-[env(safe-area-inset-bottom)]",
          "data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-full duration-200",
          /* sm+: centered dialog */
          "sm:max-w-md sm:rounded-2xl sm:shadow-2xl sm:mx-4",
          className,
        )}
        data-state="open"
        {...props}
      >
        {/* Handle bar — mobile only */}
        <div className="mx-auto mb-4 mt-3 h-1.5 w-12 rounded-full bg-toss-border sm:hidden" aria-hidden="true" />
        {children}
      </div>
    </div>
  );
}

/* ── Header ─────────────────────────────────────────────────────────────── */

function BottomSheetHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mb-4 flex flex-col space-y-1", className)}
      {...props}
    />
  );
}

/* ── Title ──────────────────────────────────────────────────────────────── */

function BottomSheetTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn("text-2xl font-bold text-toss-textStrong", className)}
      {...props}
    />
  );
}

/* ── Footer ─────────────────────────────────────────────────────────────── */

function BottomSheetFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)}
      {...props}
    />
  );
}

export {
  BottomSheet,
  BottomSheetTrigger,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetFooter,
};
