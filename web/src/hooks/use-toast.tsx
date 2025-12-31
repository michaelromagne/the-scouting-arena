"use client";

import * as React from "react";

export type ToastVariant = "default" | "destructive";

export type ToastInput = {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
};

type ToastState = ToastInput & {
  id: string;
  open: boolean;
};

type ToastContextValue = {
  toasts: ToastState[];
  toast: (input: ToastInput) => void;
  dismiss: (id?: string) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

function genId(): string {
  // No crypto dependency; stable enough for UI toasts.
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastState[]>([]);

  const dismiss = React.useCallback((id?: string) => {
    setToasts((prev) =>
      id
        ? prev.map((t) => (t.id === id ? { ...t, open: false } : t))
        : prev.map((t) => ({ ...t, open: false }))
    );
  }, []);

  const toast = React.useCallback(
    (input: ToastInput) => {
      const id = genId();
      const duration = input.duration ?? 3500;

      setToasts((prev) => [{ ...input, id, open: true }, ...prev].slice(0, 5));

      window.setTimeout(() => {
        dismiss(id);
        window.setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 300);
      }, duration);
    },
    [dismiss]
  );

  const value = React.useMemo<ToastContextValue>(
    () => ({ toasts, toast, dismiss }),
    [toasts, toast, dismiss]
  );

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within <ToastProvider />");
  }
  return { toast: ctx.toast, dismiss: ctx.dismiss, toasts: ctx.toasts };
}
