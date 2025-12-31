"use client";

import * as React from "react";
import { Toast } from "@/components/ui/toast";
import { useToast } from "@/hooks/use-toast";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div
      aria-live="polite"
      aria-relevant="additions text"
      className="pointer-events-none fixed right-4 top-4 z-50 flex w-full flex-col gap-2 sm:max-w-sm"
    >
      {toasts.map((t) => (
        <div key={t.id} className="relative">
          <Toast
            variant={t.variant}
            title={t.title}
            description={t.description}
            open={t.open}
            onOpenChange={(open) => {
              if (!open) dismiss(t.id);
            }}
          />
        </div>
      ))}
    </div>
  );
}
