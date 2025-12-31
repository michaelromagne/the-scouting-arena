"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const toastVariants = cva(
  "pointer-events-auto w-full max-w-sm rounded-lg border p-4 shadow-lg transition-all",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive: "border-red-200 bg-red-50 text-red-900",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export type ToastProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof toastVariants> & {
    title?: string;
    description?: string;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
  };

export function Toast({
  className,
  variant,
  title,
  description,
  open = true,
  onOpenChange,
  ...props
}: ToastProps) {
  if (!open) return null;

  return (
    <div className={cn(toastVariants({ variant }), className)} {...props}>
      <div className="grid gap-1">
        {title ? <div className="text-sm font-semibold">{title}</div> : null}
        {description ? (
          <div className="text-sm text-muted-foreground">{description}</div>
        ) : null}
      </div>
      <button
        type="button"
        aria-label="Close"
        className="absolute right-2 top-2 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
        onClick={() => onOpenChange?.(false)}
      >
        Close
      </button>
    </div>
  );
}
