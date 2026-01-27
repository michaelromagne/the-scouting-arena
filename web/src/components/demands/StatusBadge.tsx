"use client";

import { Badge } from "@/components/ui/badge";

interface StatusBadgeProps {
  status: "suggested" | "proposed" | "interested" | "rejected" | "signed" | "open" | "closed";
  className?: string;
}

const statusConfig = {
  suggested: {
    label: "Suggested",
    className: "bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-800 dark:text-gray-200",
  },
  proposed: {
    label: "Proposed",
    className: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900 dark:text-blue-200",
  },
  interested: {
    label: "Interested",
    className: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200",
  },
  signed: {
    label: "Signed",
    className: "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900 dark:text-purple-200",
  },
  open: {
    label: "Open",
    className: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200",
  },
  closed: {
    label: "Closed",
    className: "bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-800 dark:text-gray-200",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge className={`${config.className} ${className || ""}`}>
      {config.label}
    </Badge>
  );
}
