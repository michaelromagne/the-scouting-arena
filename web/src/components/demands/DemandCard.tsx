"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "./StatusBadge";
import type { DemandSummary } from "@/lib/api/demands";

interface DemandCardProps {
  demand: DemandSummary;
}

export function DemandCard({ demand }: DemandCardProps) {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getDeadlineColor = (deadline: string | null) => {
    if (!deadline) return "";
    const daysUntil = Math.ceil(
      (new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    if (daysUntil < 0) return "text-red-600 dark:text-red-400";
    if (daysUntil < 7) return "text-orange-600 dark:text-orange-400";
    return "text-gray-600 dark:text-gray-400";
  };

  const totalMatches = Object.values(demand.match_counts).reduce((a, b) => a + b, 0);

  return (
    <Link href={`/demands/${demand.id}`}>
      <Card className="p-4 hover:shadow-lg transition-shadow cursor-pointer">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <h3 className="text-lg font-semibold">{demand.club_name}</h3>
            <div className="flex gap-2 mt-2 flex-wrap">
              {demand.position.map((pos) => (
                <Badge key={pos} variant="outline">
                  {pos}
                </Badge>
              ))}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <StatusBadge status={demand.status} />
            <Badge
              variant={
                demand.priority === "high"
                  ? "destructive"
                  : demand.priority === "medium"
                    ? "default"
                    : "secondary"
              }
            >
              {demand.priority}
            </Badge>
          </div>
        </div>

        <div className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Created:</span>
            <span>{formatDate(demand.created_date)}</span>
          </div>
          {demand.deadline && (
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Deadline:</span>
              <span className={getDeadlineColor(demand.deadline)}>
                {formatDate(demand.deadline)}
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Total Matches:</span>
            <span className="font-semibold">{totalMatches}</span>
          </div>
        </div>

        {totalMatches > 0 && (
          <div className="mt-4 pt-4 border-t flex justify-between text-xs">
            {demand.match_counts.suggested > 0 && (
              <div className="text-center">
                <div className="font-semibold">{demand.match_counts.suggested}</div>
                <div className="text-gray-500">Suggested</div>
              </div>
            )}
            {demand.match_counts.proposed > 0 && (
              <div className="text-center">
                <div className="font-semibold text-blue-600">{demand.match_counts.proposed}</div>
                <div className="text-gray-500">Proposed</div>
              </div>
            )}
            {demand.match_counts.interested > 0 && (
              <div className="text-center">
                <div className="font-semibold text-green-600">{demand.match_counts.interested}</div>
                <div className="text-gray-500">Interested</div>
              </div>
            )}
            {demand.match_counts.signed > 0 && (
              <div className="text-center">
                <div className="font-semibold text-purple-600">{demand.match_counts.signed}</div>
                <div className="text-gray-500">Signed</div>
              </div>
            )}
          </div>
        )}
      </Card>
    </Link>
  );
}
