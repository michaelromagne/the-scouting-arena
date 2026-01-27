"use client";

import Link from "next/link";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "./StatusBadge";
import type { DemandMatch } from "@/lib/api/demands";

interface MatchPlayerCardProps {
  match: DemandMatch;
  onStatusChange?: (playerId: number, status: DemandMatch["status"]) => void;
  onNotesChange?: (playerId: number, notes: string) => void;
  onRemove?: (playerId: number) => void;
}

export function MatchPlayerCard({
  match,
  onStatusChange,
  onNotesChange,
  onRemove,
}: MatchPlayerCardProps) {
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [notes, setNotes] = useState(match.notes || "");

  const { player } = match;

  const handleNotesSubmit = () => {
    onNotesChange?.(player.id, notes);
    setIsEditingNotes(false);
  };

  const calculateAge = (birthDate: string | null) => {
    if (!birthDate) return null;
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  return (
    <Card className="p-4">
      <div className="flex gap-4">
        {/* Player Image */}
        <div className="flex-shrink-0">
          <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-gray-200">
            {player.image_url ? (
              <img
                src={player.image_url}
                alt={player.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.src = `https://via.placeholder.com/80x80/f1f5f9/64748b?text=${encodeURIComponent(
                    player.name.charAt(0)
                  )}`;
                }}
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
                <span className="text-2xl font-bold text-slate-400">
                  {player.name.charAt(0)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Player Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-2">
            <div>
              <Link
                href={`/talent-pool/${player.id}`}
                className="text-lg font-semibold hover:text-blue-600 transition-colors"
              >
                {player.name}
              </Link>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {player.team && player.league && (
                  <span>
                    {player.team} • {player.league}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-right">
                <div className="text-sm font-semibold text-green-600">
                  {(match.match_score * 100).toFixed(0)}% match
                </div>
              </div>
            </div>
          </div>

          {/* Player Details */}
          <div className="flex gap-2 flex-wrap mb-3">
            {player.position && <Badge variant="outline">{player.position}</Badge>}
            {player.age && <Badge variant="outline">{player.age}yo</Badge>}
            {player.nationality && <Badge variant="outline">{player.nationality}</Badge>}
            {player.market_value && (
              <Badge variant="outline">
                €{(player.market_value / 1_000_000).toFixed(1)}M
              </Badge>
            )}
          </div>

          {/* Key Metrics */}
          {Object.keys(player.key_metrics).length > 0 && (
            <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
                Key Metrics
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(player.key_metrics).map(([metric, value]) => (
                  <div key={metric}>
                    <span className="text-gray-600 dark:text-gray-400">
                      {metric.replace(/_/g, " ")}:
                    </span>{" "}
                    <span className="font-semibold">{value.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Status and Actions */}
          <div className="flex items-center gap-3 mb-3">
            <Select
              value={match.status}
              onValueChange={(value) =>
                onStatusChange?.(player.id, value as DemandMatch["status"])
              }
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="suggested">Suggested</SelectItem>
                <SelectItem value="proposed">Proposed</SelectItem>
                <SelectItem value="interested">Interested</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="signed">Signed</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditingNotes(!isEditingNotes)}
            >
              {isEditingNotes ? "Cancel" : "Notes"}
            </Button>
            {onRemove && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onRemove(player.id)}
              >
                Remove
              </Button>
            )}
          </div>

          {/* Notes Section */}
          {isEditingNotes ? (
            <div className="space-y-2">
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this player..."
                className="min-h-20"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleNotesSubmit}>
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setNotes(match.notes || "");
                    setIsEditingNotes(false);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            match.notes && (
              <div className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 p-2 rounded">
                {match.notes}
              </div>
            )
          )}
        </div>
      </div>
    </Card>
  );
}
