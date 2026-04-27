import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

/* MODIFIED: Toss-style input — rounded-xl, toss-border, toss-card bg, text-base (iOS zoom prevention) */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-12 w-full rounded-xl border border-toss-border bg-toss-card px-4 text-base text-toss-textStrong placeholder:text-toss-textDisabled transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus:border-toss-blue focus:outline-none focus:ring-2 focus:ring-toss-blue/20 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
