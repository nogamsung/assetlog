"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Traps keyboard focus inside `containerRef` while `isOpen` is true.
 * Moves focus to the first focusable element (or the container itself) on open.
 * Restores focus to the previously-focused element on close.
 * Pure side-effect hook — returns nothing.
 */
export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  isOpen: boolean,
): void {
  // Store the element that had focus before the trap opened.
  const previousFocusRef = useRef<Element | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    // Save current focus target before we move focus.
    previousFocusRef.current = document.activeElement;

    const container = containerRef.current;
    if (!container) return;

    // Move focus into the sheet: first focusable child, else the container.
    const focusable = Array.from(
      container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    ).filter((el) => !el.closest("[aria-hidden='true']"));

    if (focusable.length > 0) {
      focusable[0].focus();
    } else {
      // Ensure the container itself can receive focus as fallback.
      container.focus();
    }

    function handleKeyDown(e: KeyboardEvent): void {
      if (e.key !== "Tab") return;

      const inner = Array.from(
        container!.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter((el) => !el.closest("[aria-hidden='true']"));

      if (inner.length === 0) {
        e.preventDefault();
        return;
      }

      const first = inner[0];
      const last = inner[inner.length - 1];

      if (e.shiftKey) {
        // Shift+Tab: if focus is at (or before) first → wrap to last.
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab: if focus is at (or after) last → wrap to first.
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [containerRef, isOpen]);

  // Restore focus when the sheet closes.
  useEffect(() => {
    if (isOpen) return;
    const prev = previousFocusRef.current;
    if (prev && "focus" in prev) {
      (prev as HTMLElement).focus();
    }
  }, [isOpen]);
}
