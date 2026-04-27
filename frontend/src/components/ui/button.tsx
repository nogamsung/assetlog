import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/* MODIFIED: Toss design tokens applied to all variants + icon-touch size */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-toss-blue/30 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        /* MODIFIED: Toss-blue primary */
        default:
          "bg-toss-blue text-white font-bold active:scale-[0.98] hover:brightness-95",
        /* MODIFIED: Toss destructive (bg-toss-up/10) */
        destructive:
          "bg-toss-up/10 text-toss-up font-bold active:scale-[0.98]",
        /* MODIFIED: Toss outline */
        outline:
          "border border-toss-border bg-transparent text-toss-text hover:bg-toss-card active:scale-[0.98]",
        /* MODIFIED: Toss secondary card */
        secondary:
          "bg-toss-card text-toss-text border border-toss-border active:scale-[0.98] hover:bg-toss-border",
        /* MODIFIED: Toss ghost */
        ghost: "text-toss-text hover:bg-toss-card active:scale-[0.98]",
        link: "text-toss-blue underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-8",
        icon: "h-9 w-9",
        "icon-touch": "h-11 w-11", /* ADDED: 44px tap target for mobile */
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
